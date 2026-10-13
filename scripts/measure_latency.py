"""Ingest one flood-like reading and measure time until the alert is visible via the API."""
import os
import sys
import time
from datetime import datetime, timezone

import httpx

BASE = os.environ.get("API_URL", "http://localhost:8000")
PASSWORD = os.environ.get("DEMO_PASSWORD")
if not PASSWORD:
    sys.exit("Set DEMO_PASSWORD (same value as in .env)")

with httpx.Client(base_url=BASE, timeout=10) as c:
    token = c.post("/auth/login", json={"username": "analyst", "password": PASSWORD}).json()[
        "access_token"
    ]
    h = {"Authorization": f"Bearer {token}"}
    before = {a["id"] for a in c.get("/alerts", headers=h).json()}
    payload = {
        "station_id": f"SAWS-DBN{int(time.time()) % 100000}",
        "region_id": "KZN-ETHEKWINI",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "lat": -29.85, "lon": 31.02,
        "rainfall_mm_24h": 180, "river_level_m": 6.5, "soil_moisture": 0.92,
        "temperature_c": 21, "humidity_pct": 95,
    }
    t0 = time.perf_counter()
    r = c.post("/ingest/weather", json=payload, headers=h)
    r.raise_for_status()
    while time.perf_counter() - t0 < 60:
        new = [a for a in c.get("/alerts", headers=h).json() if a["id"] not in before]
        if new:
            dt = time.perf_counter() - t0
            print(f"Alert {new[0]['id']} ({new[0]['severity']}) visible after {dt:.3f}s "
                  f"(server-side latency {new[0]['latency_ms']:.1f} ms) - target < 60s")
            break
        time.sleep(0.1)
    else:
        sys.exit("FAILED: no alert within 60s")