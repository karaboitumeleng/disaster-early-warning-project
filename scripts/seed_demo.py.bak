"""Seed SYNTHETIC readings (last 48 hours, hourly) so the dashboard has content offline.
Idempotent within the same hour: re-running produces duplicates that the API ignores."""
import os
import random
import sys
from datetime import datetime, timedelta, timezone

import httpx

BASE = os.environ.get("API_URL", "http://localhost:8000")
PASSWORD = os.environ.get("DEMO_PASSWORD")
if not PASSWORD:
    sys.exit("Set DEMO_PASSWORD (same value as in .env)")

REGIONS = {
    "KZN-ETHEKWINI": (-29.86, 31.02),
    "KZN-ILEMBE": (-29.33, 31.29),
    "KZN-UGU": (-30.74, 30.45),
    "KZN-UMGUNGUNDLOVU": (-29.60, 30.38),
    "KZN-UTHUKELA": (-28.56, 29.78),
    "KZN-KING-CETSHWAYO": (-28.78, 32.04),
    "MP-EHLANZENI": (-25.47, 30.98),
    "MP-GERT-SIBANDE": (-26.53, 29.98),
    "MP-NKANGALA": (-25.77, 29.46),
}
STORM = {"KZN-ETHEKWINI": 180.0, "KZN-UGU": 120.0}  # peak 24h rainfall (mm) in the last 4 hours
HOURS = 48
now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)

with httpx.Client(base_url=BASE, timeout=15) as c:
    r = c.post("/auth/login", json={"username": "analyst", "password": PASSWORD})
    r.raise_for_status()
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    accepted = duplicate = 0
    for step in range(HOURS):
        ts = now - timedelta(hours=HOURS - 1 - step)
        for rid, (lat, lon) in REGIONS.items():
            rng = random.Random(f"{rid}-{ts.isoformat()}")
            rain = rng.uniform(2, 18)
            peak = STORM.get(rid)
            if peak and step >= HOURS - 4:
                rain = peak * (0.35 + 0.65 * (step - (HOURS - 4)) / 3)
            payload = {
                "station_id": f"SAWS-{rid}",
                "region_id": rid,
                "observed_at": ts.isoformat(),
                "lat": lat,
                "lon": lon,
                "rainfall_mm_24h": round(rain, 1),
                "river_level_m": round(0.6 + rain / 30, 2),
                "soil_moisture": round(min(0.95, 0.25 + rain / 200), 2),
                "temperature_c": round(rng.uniform(17, 27), 1),
                "humidity_pct": round(min(100.0, 55 + rain / 3), 1),
            }
            resp = c.post("/ingest/weather", json=payload, headers=h)
            resp.raise_for_status()
            if resp.json()["status"] == "accepted":
                accepted += 1
            else:
                duplicate += 1
    print(f"Seeded synthetic data: {accepted} accepted, {duplicate} duplicates ignored.")
