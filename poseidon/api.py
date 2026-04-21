"""
POSEIDON-OS — REST API
Flask API che espone gli endpoint del sistema.
Installabile e runnabile localmente con: python api.py
"""
import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, jsonify, request
from poseidon.ingestor import search_sentinel2, fetch_ais_vessels
from poseidon.detector import run_detection, image_to_base64
from poseidon.analyzer import analyze_vessel_activity, generate_historical_baseline, PORTS_OF_INTEREST

app = Flask(__name__)

@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "system": "POSEIDON-OS",
        "version": "0.1.0-poc",
        "status": "operational",
        "description": "Maritime port intelligence via open-source satellite imagery",
        "endpoints": {
            "GET /ports": "List monitored ports",
            "GET /analyze/<port_key>": "Full intelligence analysis for a port",
            "GET /satellite/<port_key>": "Search available Sentinel-2 imagery",
            "GET /ais/<port_key>": "Get AIS vessel data for port area",
            "GET /history/<port_key>": "Get 14-day activity baseline",
            "GET /detect/<port_key>": "Run ship detection on synthetic satellite image"
        }
    })

@app.route("/ports", methods=["GET"])
def list_ports():
    return jsonify({
        "ports": [
            {**{"key": k}, **{k2: v2 for k2, v2 in v.items() if k2 != "bbox"}}
            for k, v in PORTS_OF_INTEREST.items()
        ]
    })

@app.route("/analyze/<port_key>", methods=["GET"])
def analyze_port(port_key):
    if port_key not in PORTS_OF_INTEREST:
        return jsonify({"error": f"Port '{port_key}' not found. Use /ports to list available ports."}), 404
    
    port = PORTS_OF_INTEREST[port_key]
    bbox = port["bbox"]
    
    # Recupera dati AIS
    vessels = fetch_ais_vessels(bbox)
    
    # Simula detections satellite (in produzione: run_detection su vera immagine)
    _, detections = run_detection(port_name=port["name"], vessel_count=len(vessels) + 1)
    
    # Analisi intelligence
    report = analyze_vessel_activity(port_key, vessels, detections)
    
    return jsonify(report)

@app.route("/satellite/<port_key>", methods=["GET"])
def satellite_search(port_key):
    if port_key not in PORTS_OF_INTEREST:
        return jsonify({"error": "Port not found"}), 404
    
    port = PORTS_OF_INTEREST[port_key]
    days_back = request.args.get("days", 30, type=int)
    
    products = search_sentinel2(port["bbox"], days_back=days_back)
    return jsonify({
        "port": port["name"],
        "days_searched": days_back,
        "products_found": len(products),
        "products": products
    })

@app.route("/ais/<port_key>", methods=["GET"])
def ais_data(port_key):
    if port_key not in PORTS_OF_INTEREST:
        return jsonify({"error": "Port not found"}), 404
    
    port = PORTS_OF_INTEREST[port_key]
    vessels = fetch_ais_vessels(port["bbox"])
    
    return jsonify({
        "port": port["name"],
        "vessel_count": len(vessels),
        "vessels": vessels
    })

@app.route("/history/<port_key>", methods=["GET"])
def history(port_key):
    days = request.args.get("days", 14, type=int)
    baseline = generate_historical_baseline(port_key, days)
    return jsonify({
        "port_key": port_key,
        "days": days,
        "baseline": baseline
    })

@app.route("/detect/<port_key>", methods=["GET"])
def detect(port_key):
    port = PORTS_OF_INTEREST.get(port_key, {"name": port_key})
    vessels_count = request.args.get("vessels", 5, type=int)
    
    img, detections = run_detection(port_name=port["name"], vessel_count=vessels_count)
    img_b64 = image_to_base64(img)
    
    return jsonify({
        "port": port["name"],
        "detections": detections,
        "vessel_count": len(detections),
        "image_base64": img_b64,
        "note": "Synthetic satellite image for POC. Replace with real Sentinel-2 data."
    })

if __name__ == "__main__":
    print("\n🌊 POSEIDON-OS POC — Starting...\n")
    print("Endpoints:")
    print("  http://localhost:5000/")
    print("  http://localhost:5000/ports")
    print("  http://localhost:5000/analyze/sevastopol")
    print("  http://localhost:5000/detect/sevastopol")
    print("  http://localhost:5000/history/sevastopol\n")
    app.run(debug=True, host="0.0.0.0", port=5000)

