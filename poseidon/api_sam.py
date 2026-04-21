"""
POSEIDON-OS — SAM Hunter API Endpoint
Aggiunge /scan/sam alla Flask API esistente.
Triggera pipeline SAM Hunter su nuova immagine + alert Telegram se conf > 85%.
"""

from flask import Flask, request, jsonify
import os
import json
import base64
import urllib.request
import urllib.parse
from io import BytesIO
from PIL import Image
import numpy as np
import uuid
from datetime import datetime, timezone

from poseidon.sam_hunter.sam_hunter import SAMHunter, render_annotated_image
from poseidon.sam_hunter.scene_generator import generate_sam_scene

app = Flask(__name__)

# ── Config ──
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
CONFIDENCE_ALERT_THRESHOLD = 0.85

hunter = SAMHunter(resolution_mpp=0.5)


# ─────────────────────────────────────────────
# TELEGRAM NOTIFIER
# ─────────────────────────────────────────────

def send_telegram_alert(result: dict, image: Image.Image = None):
    """
    Invia alert su Telegram quando conf > 85%.
    Manda testo + immagine annotata.
    """
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("[TELEGRAM] No token/chat_id configured — skipping notification")
        return False

    batteries = result.get("batteries", [])
    summary = result.get("summary", {})
    alert = result.get("overall_alert_level", "UNKNOWN")
    area = result.get("area", "Unknown")
    scan_id = result.get("scan_id", "N/A")

    alert_emoji = {
        "CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"
    }.get(alert, "⚪")

    # Costruisci messaggio
    msg_lines = [
        f"{alert_emoji} *POSEIDON-OS SAM HUNTER ALERT*",
        f"",
        f"📍 *Area:* {area}",
        f"⏱ *Time:* {result.get('timestamp_utc', 'N/A')} UTC",
        f"🆔 *Scan ID:* `{scan_id}`",
        f"",
        f"*ALERT LEVEL: {alert}*",
        f"",
        f"📊 *Summary:*",
        f"  • Batteries identified: {summary.get('batteries_identified', 0)}",
        f"  • TEL launchers: {summary.get('tel_count', 0)}",
        f"  • Radars: {summary.get('radar_count', 0)}",
        f"  • Decoys neutralized: {summary.get('decoys_identified', 0)}",
        f"",
    ]

    for b in batteries[:3]:  # Max 3 batterie nel messaggio
        conf_pct = int(b['Confidence_Score'] * 100)
        coords = b['Center_Coordinates']
        msg_lines += [
            f"🎯 *{b['Battery_ID']}*",
            f"  Type: {b['Battery_Type']}",
            f"  Pattern: {b['Deployment_Pattern']}",
            f"  Confidence: {conf_pct}%",
            f"  Active: {'Yes' if b['Is_Active'] else 'No'}",
            f"  📌 `{coords['lat']}, {coords['lon']}`",
            f"  [Open in Maps](https://maps.google.com/?q={coords['lat']},{coords['lon']})",
            f"",
        ]

    msg_lines.append("_POSEIDON-OS | Open-source maritime & air defense intelligence_")
    message_text = "\n".join(msg_lines)

    # Invia immagine annotata se disponibile
    if image:
        try:
            annotated = render_annotated_image(image, result)
            buf = BytesIO()
            annotated.save(buf, format="PNG")
            buf.seek(0)

            boundary = "PoseidonBoundary"
            body_parts = []
            body_parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"chat_id\"\r\n\r\n{TELEGRAM_CHAT_ID}".encode())
            body_parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"caption\"\r\n\r\n{message_text}".encode())
            body_parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"parse_mode\"\r\n\r\nMarkdown".encode())
            body_parts.append(
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"photo\"; filename=\"sam_scan.png\"\r\nContent-Type: image/png\r\n\r\n".encode()
                + buf.read()
            )
            body_parts.append(f"--{boundary}--\r\n".encode())
            body = b"\r\n".join(body_parts)

            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
            req = urllib.request.Request(url, data=body,
                                          headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                resp.read()
                print("[TELEGRAM] Alert + image sent ✅")
                return True
        except Exception as e:
            print(f"[TELEGRAM] Image send failed: {e} — falling back to text")

    # Fallback: solo testo
    try:
        payload = json.dumps({
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message_text,
            "parse_mode": "Markdown"
        }).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
            print("[TELEGRAM] Text alert sent ✅")
            return True
    except Exception as e:
        print(f"[TELEGRAM] Text send failed: {e}")
        return False


# ─────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────

@app.route("/scan/sam", methods=["POST"])
def scan_sam():
    """
    Trigger SAM Hunter su una nuova immagine.

    Body JSON:
    {
      "area": "Crimea — Sevastopol",
      "origin_lat": 44.60,
      "origin_lon": 33.52,
      "image_base64": "<base64 encoded PNG/JPG>",   ← opzionale (usa scena sintetica se assente)
      "use_synthetic": true                           ← forza scena sintetica
    }

    Response: intelligence JSON completo
    """
    data = request.get_json(force=True, silent=True) or {}

    area = data.get("area", "Unknown Area")
    origin_lat = float(data.get("origin_lat", 44.95))
    origin_lon = float(data.get("origin_lon", 34.10))
    use_synthetic = data.get("use_synthetic", False)
    image_b64 = data.get("image_base64", None)

    # Carica o genera immagine
    ground_truth = []
    if image_b64 and not use_synthetic:
        try:
            img_bytes = base64.b64decode(image_b64)
            img = Image.open(BytesIO(img_bytes)).convert("RGB")
            # In produzione: YOLOv8 reale, nessun ground_truth necessario
            # Per ora usiamo synthetic overlay per POC
            _, ground_truth = generate_sam_scene(seed=42)
        except Exception as e:
            return jsonify({"error": f"Image decode failed: {e}"}), 400
    else:
        # Scena sintetica
        import random
        seed = random.randint(0, 9999)
        img, ground_truth = generate_sam_scene(scenario="active_battery", seed=seed)

    # Esegui pipeline
    result = hunter.process_image(
        img, ground_truth,
        origin_lat=origin_lat,
        origin_lon=origin_lon,
        area_name=area
    )

    # Alert Telegram se confidence > soglia
    triggered_alert = False
    max_conf = max((b["Confidence_Score"] for b in result.get("batteries", [])), default=0)

    if max_conf >= CONFIDENCE_ALERT_THRESHOLD:
        triggered_alert = send_telegram_alert(result, img)

    result["telegram_alert_sent"] = triggered_alert
    result["alert_threshold"] = CONFIDENCE_ALERT_THRESHOLD

    return jsonify(result), 200


@app.route("/scan/sam/demo", methods=["GET"])
def scan_sam_demo():
    """Demo endpoint — genera scena attiva e restituisce intelligence report."""
    img, ground_truth = generate_sam_scene(scenario="active_battery", seed=99)
    result = hunter.process_image(
        img, ground_truth,
        origin_lat=44.60, origin_lon=33.52,
        area_name="Crimea — Sevastopol (Demo)"
    )
    result["note"] = "Synthetic scene — demo mode"
    return jsonify(result), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "module": "POSEIDON-OS SAM Hunter", "version": "0.2.0"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=False)
