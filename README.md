# POSEIDON-OS
**Free, open-source maritime port intelligence platform.**

Fuses ESA Sentinel-2 satellite imagery with public AIS transponder data to monitor hostile naval ports in near-real-time.

## Target ports
- Sevastopol Naval Base
- Novorossiysk Port
- Kerch Strait

## Capabilities
- YOLOv8 ship detection on Sentinel-2 optical imagery (10m resolution)
- AIS fusion — cross-reference satellite detections vs transponder data
- **Dark vessel identification** — ships visible from satellite but NOT broadcasting AIS
- 14-day activity baseline + anomaly detection
- REST API — 7 endpoints, JSON intelligence reports

## Sample output
```json
{
  "port": "Sevastopol Naval Base",
  "threat_level": "HIGH",
  "vessel_count": { "satellite": 6, "ais": 5, "dark": 1 },
  "alerts": [
    "2 landing ships detected — potential amphibious activity",
    "1 dark vessel — possible military/covert ops"
  ]
}
```

## Quick start
```bash
git clone https://github.com/P-create-sumo/poseidon
cd poseidon
pip install -r requirements.txt
python poseidon/api.py
curl http://localhost:5000/analyze/sevastopol
```

## License
MIT — free forever
