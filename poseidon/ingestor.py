"""
POSEIDON-OS — Data Ingestor
Scarica immagini Sentinel-2 da Copernicus Open Access Hub (ESA)
usando l'API pubblica. Nessuna chiave necessaria per dati > 12 mesi.
Per dati recenti usa Copernicus Data Space (richiede account gratuito).
"""
import os
import json
import requests
from datetime import datetime, timedelta
from pathlib import Path

COPERNICUS_API = "https://catalogue.dataspace.copernicus.eu/odata/v1"

def search_sentinel2(bbox: dict, days_back: int = 30, cloud_cover: int = 20) -> list:
    """
    Cerca immagini Sentinel-2 sull'area di interesse.
    bbox: {"west": float, "east": float, "south": float, "north": float}
    Ritorna lista di prodotti disponibili.
    """
    # Costruisci WKT polygon dalla bbox
    w, e, s, n = bbox["west"], bbox["east"], bbox["south"], bbox["north"]
    wkt = f"POLYGON(({w} {s},{e} {s},{e} {n},{w} {n},{w} {s}))"
    
    date_end = datetime.utcnow()
    date_start = date_end - timedelta(days=days_back)
    
    params = {
        "$filter": (
            f"Collection/Name eq 'SENTINEL-2' "
            f"and OData.CSC.Intersects(area=geography'SRID=4326;{wkt}') "
            f"and ContentDate/Start gt {date_start.strftime('%Y-%m-%dT%H:%M:%S.000Z')} "
            f"and ContentDate/Start lt {date_end.strftime('%Y-%m-%dT%H:%M:%S.000Z')} "
            f"and Attributes/OData.CSC.DoubleAttribute/any(att:att/Name eq 'cloudCover' and att/OData.CSC.DoubleAttribute/Value lt {cloud_cover})"
        ),
        "$orderby": "ContentDate/Start desc",
        "$top": "5",
        "$expand": "Attributes"
    }
    
    try:
        r = requests.get(f"{COPERNICUS_API}/Products", params=params, timeout=15)
        r.raise_for_status()
        products = r.json().get("value", [])
        return [{
            "id": p["Id"],
            "name": p["Name"],
            "date": p["ContentDate"]["Start"],
            "size_mb": round(p.get("ContentLength", 0) / 1e6, 1),
            "cloud_cover": next(
                (a["Value"] for a in p.get("Attributes", []) if a.get("Name") == "cloudCover"),
                "N/A"
            )
        } for p in products]
    except Exception as e:
        return [{"error": str(e)}]


def fetch_ais_vessels(bbox: dict) -> list:
    """
    Recupera dati AIS pubblici dall'area di interesse.
    Usa MarineTraffic API pubblica / VesselFinder open endpoint.
    Per il POC usiamo aisstream.io (WebSocket) o dati mock strutturati.
    """
    # Per il POC: dati AIS mock strutturati realisticamente
    # In produzione: sostituire con aisstream.io o barentswatch.no (gratuiti)
    mock_vessels = [
        {"mmsi": "212345678", "name": "ADMIRAL KUZNETSOV", "type": "Warship",
         "lat": 44.62, "lon": 33.53, "speed": 0.0, "heading": 270,
         "status": "Moored", "last_seen": "2026-04-14T18:30:00Z", "flag": "RU"},
        {"mmsi": "273456789", "name": "MOSKVA-CLASS-01", "type": "Warship",
         "lat": 44.61, "lon": 33.51, "speed": 0.0, "heading": 180,
         "status": "Moored", "last_seen": "2026-04-14T17:45:00Z", "flag": "RU"},
        {"mmsi": "273567890", "name": "CAESAR KUNIKOV", "type": "Landing Ship",
         "lat": 44.59, "lon": 33.49, "speed": 2.1, "heading": 45,
         "status": "UnderWayUsingEngine", "last_seen": "2026-04-14T19:00:00Z", "flag": "RU"},
        {"mmsi": "273678901", "name": "TAPIR-CLASS-LST", "type": "Landing Ship",
         "lat": 44.63, "lon": 33.55, "speed": 0.0, "heading": 90,
         "status": "Moored", "last_seen": "2026-04-14T16:20:00Z", "flag": "RU"},
        {"mmsi": "273789012", "name": "VASILY BYKOV", "type": "Patrol Vessel",
         "lat": 44.58, "lon": 33.47, "speed": 8.3, "heading": 320,
         "status": "UnderWayUsingEngine", "last_seen": "2026-04-14T19:10:00Z", "flag": "RU"},
    ]
    
    # Filtra per bbox
    filtered = [
        v for v in mock_vessels
        if bbox["south"] <= v["lat"] <= bbox["north"]
        and bbox["west"] <= v["lon"] <= bbox["east"]
    ]
    return filtered
