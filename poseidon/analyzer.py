"""
POSEIDON-OS — Intelligence Analyzer
Incrocia dati AIS + satellite detection + storico per generare
alert di intelligence navale.
"""
from datetime import datetime, timedelta
import json
import random

# Porte di interesse per la difesa ucraina
PORTS_OF_INTEREST = {
    "sevastopol": {
        "name": "Sevastopol Naval Base",
        "country": "RU (Occupied UA)",
        "bbox": {"west": 33.40, "east": 33.65, "south": 44.55, "north": 44.70},
        "strategic_value": "PRIMARY",
        "notes": "Main Black Sea Fleet HQ. Monitor for sortie activity and fleet composition changes."
    },
    "novorossiysk": {
        "name": "Novorossiysk Naval Base",
        "country": "RU",
        "bbox": {"west": 37.70, "east": 37.90, "south": 44.70, "north": 44.85},
        "strategic_value": "HIGH",
        "notes": "Secondary Black Sea Fleet base. Used after Sevastopol losses."
    },
    "kerch": {
        "name": "Kerch Strait",
        "country": "RU (Occupied UA)",
        "bbox": {"west": 36.35, "east": 36.60, "south": 45.25, "north": 45.45},
        "strategic_value": "HIGH",
        "notes": "Logistic chokepoint. Monitor landing ship concentration."
    },
    "bosphorus": {
        "name": "Bosphorus Strait",
        "country": "TR",
        "bbox": {"west": 28.95, "east": 29.15, "south": 40.95, "north": 41.25},
        "strategic_value": "MONITOR",
        "notes": "Transit monitoring only. Montreux Convention applies."
    }
}


def analyze_vessel_activity(port_key: str, vessels: list, detections: list) -> dict:
    """
    Analizza attività navale e genera intelligence report.
    """
    port = PORTS_OF_INTEREST.get(port_key, {
        "name": "Unknown Port",
        "strategic_value": "UNKNOWN",
        "notes": ""
    })
    
    now = datetime.utcnow()
    
    # Classifica navi per tipo
    warships = [v for v in vessels if "Warship" in v.get("type", "")]
    landing = [v for v in vessels if "Landing" in v.get("type", "")]
    underway = [v for v in vessels if v.get("status") == "UnderWayUsingEngine"]
    moored = [v for v in vessels if v.get("status") == "Moored"]
    
    # Genera threat assessment
    threat_level = "LOW"
    threat_reasons = []
    
    if len(warships) >= 3:
        threat_level = "MEDIUM"
        threat_reasons.append(f"{len(warships)} warships detected in port")
    
    if len(landing) >= 2:
        threat_level = "HIGH" if threat_level != "HIGH" else "HIGH"
        threat_reasons.append(f"{len(landing)} landing ships — potential amphibious activity")
    
    if len(underway) >= 2:
        threat_level = "HIGH"
        threat_reasons.append(f"{len(underway)} vessels underway — possible sortie in progress")
    
    # Satellite vs AIS gap (dark vessels)
    satellite_count = len(detections)
    ais_count = len(vessels)
    dark_vessels = max(0, satellite_count - ais_count)
    
    if dark_vessels > 0:
        threat_reasons.append(f"{dark_vessels} vessel(s) detected by satellite but NOT on AIS — possible dark/military ops")
        threat_level = "HIGH"
    
    # Genera SIGINT-style summary
    summary_lines = [
        f"PORT: {port['name']}",
        f"TIMESTAMP: {now.strftime('%Y-%m-%dT%H:%M:%SZ')} (UTC)",
        f"SOURCE: Sentinel-2 optical + AIS fusion",
        f"THREAT LEVEL: {threat_level}",
        "",
        "VESSEL COUNT:",
        f"  → Satellite detected: {satellite_count}",
        f"  → AIS transponders: {ais_count}",
        f"  → Dark vessels (no AIS): {dark_vessels}",
        "",
        "BREAKDOWN:",
        f"  → Warships: {len(warships)}",
        f"  → Landing ships: {len(landing)}",
        f"  → Underway: {len(underway)}",
        f"  → Moored: {len(moored)}",
    ]
    
    if threat_reasons:
        summary_lines += ["", "ALERTS:"]
        for r in threat_reasons:
            summary_lines.append(f"  ⚠ {r}")
    
    if port.get("notes"):
        summary_lines += ["", f"ANALYST NOTE: {port['notes']}"]
    
    return {
        "port": port["name"],
        "port_key": port_key,
        "timestamp": now.isoformat(),
        "threat_level": threat_level,
        "threat_reasons": threat_reasons,
        "vessel_summary": {
            "satellite_detected": satellite_count,
            "ais_tracked": ais_count,
            "dark_vessels": dark_vessels,
            "warships": len(warships),
            "landing_ships": len(landing),
            "underway": len(underway),
            "moored": len(moored),
        },
        "vessels": vessels,
        "report_text": "\n".join(summary_lines),
        "strategic_value": port.get("strategic_value", "UNKNOWN")
    }


def generate_historical_baseline(port_key: str, days: int = 14) -> list:
    """
    Genera un baseline storico simulato per confronto temporale.
    In produzione: legge dal database.
    """
    baseline = []
    now = datetime.utcnow()
    
    for i in range(days):
        date = now - timedelta(days=days - i)
        # Simula variazioni realistiche
        base_count = 8
        anomaly = random.gauss(0, 1.5)
        vessel_count = max(2, int(base_count + anomaly))
        
        baseline.append({
            "date": date.strftime("%Y-%m-%d"),
            "vessel_count": vessel_count,
            "warships": max(0, vessel_count - 3),
            "threat_level": "HIGH" if vessel_count > 11 else ("MEDIUM" if vessel_count > 8 else "LOW")
        })
    
    return baseline

