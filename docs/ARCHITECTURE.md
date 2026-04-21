# POSEIDON-OS Architecture

## Pipeline

```
Sentinel-2 API (ESA Copernicus)
        ↓
   ingestor.py  →  downloads imagery, fetches AIS data
        ↓
   detector.py  →  YOLOv8 ship detection (bounding boxes, confidence)
        ↓
   analyzer.py  →  AIS/satellite fusion, dark vessel ID, threat scoring
        ↓
    api.py       →  Flask REST API (7 endpoints)
```

## REST API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /analyze/<port>` | Full intelligence report |
| `GET /detect/<port>` | Computer vision output |
| `GET /ais/<port>` | Live AIS vessel data |
| `GET /history/<port>` | 14-day activity baseline |
| `GET /satellite/<port>` | Available Sentinel-2 images |
| `POST /scan/sam` | SAM Hunter pipeline trigger |
| `GET /scan/sam/demo` | SAM Hunter demo (synthetic) |

## Supported ports
- `sevastopol` — 44.6°N 33.5°E
- `novorossiysk` — 44.7°N 37.8°E
- `kerch` — 45.3°N 36.5°E

## Data sources
- **Sentinel-2**: ESA Copernicus (free, 10m resolution, 5-day revisit)
- **Sentinel-1**: SAR imagery for SAM Hunter (free)
- **AIS**: aisstream.io WebSocket API (free tier)
