"""Auto-seeds a realistic multi-region flood scenario the first time the app starts on an
empty database, so the dashboard is fully populated (map colours, live alerts, time-series)
the moment someone opens it — no script, no manual ingestion needed.

Feature values below were chosen by evaluating StatisticalBaselinePredictor's actual scoring
formula (not guessed) so each region lands in a specific, intentional band:
  KZN-ETHEKWINI     -> escalates to CRITICAL (mirrors the real April 2022 KZN flood)
  MP-EHLANZENI       -> escalates to WARNING
  KZN-KINGCETSHWAYO  -> escalates to WATCH / elevated band
  KZN-UMGUNGUNDLOVU  -> stays calm, LOW band, no alert (shows the map isn't just "all red")
  MP-NKANGALA        -> stays calm, then one reading far outside the training envelope,
                         demonstrating the OWML novelty-detection hook ("unrecognised pattern")

This only runs once: main.py checks ReadingRepo.has_any() first. Delete the sqlite file (or
run scripts/wipe_demo_db.ps1) to make it seed again on the next startup.
"""
from datetime import datetime, timedelta, timezone

from app.schemas import WeatherReading
from app.seed_data import DEMO_REGIONS

_CENTROID = {r.id: (r.centroid_lat, r.centroid_lon) for r in DEMO_REGIONS}


def _reading(region_id: str, station: str, days_ago: int, rain: float, river: float,
             soil: float, temp: float, humidity: float) -> WeatherReading:
    lat, lon = _CENTROID[region_id]
    observed = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return WeatherReading(
        station_id=station, region_id=region_id, observed_at=observed, lat=lat, lon=lon,
        rainfall_mm_24h=rain, river_level_m=river, soil_moisture=soil,
        temperature_c=temp, humidity_pct=humidity,
    )


# (days_ago, rain_mm, river_m, soil, temp_c, humidity_pct) — oldest first, ends "today"
_ETHEKWINI = [
    (6, 5, 0.9, 0.30, 22, 65), (5, 15, 1.1, 0.38, 21, 70), (4, 35, 1.6, 0.50, 20, 78),
    (3, 60, 2.1, 0.58, 19, 85), (2, 90, 2.5, 0.62, 18, 90),   # -> WARNING alert (~0.81)
    (1, 115, 2.8, 0.64, 18, 93),                              # -> CRITICAL alert (~0.92)
    (0, 130, 3.0, 0.65, 18, 95),                              # -> CRITICAL alert (~0.95)
]
_EHLANZENI = [
    (5, 8, 0.6, 0.30, 24, 60), (4, 20, 0.8, 0.38, 23, 68), (3, 45, 1.0, 0.42, 22, 74),
    (2, 70, 1.2, 0.46, 21, 80),
    (1, 95, 1.4, 0.49, 20, 85),                               # -> WATCH alert (~0.70)
    (0, 110, 1.5, 0.50, 20, 88),                               # -> WARNING alert (~0.80)
]
_KINGCETSHWAYO = [
    (4, 10, 0.4, 0.30, 25, 62), (3, 25, 0.5, 0.35, 24, 68), (2, 45, 0.7, 0.42, 23, 74),
    (1, 70, 0.9, 0.50, 22, 78),
    (0, 90, 1.0, 0.55, 22, 80),                                # -> WATCH alert (~0.64)
]
_UMGUNGUNDLOVU = [  # stays calm on purpose — proves the map isn't uniformly red
    (3, 3, 0.7, 0.25, 23, 55), (2, 2, 0.7, 0.24, 24, 52),
    (1, 4, 0.75, 0.26, 23, 58), (0, 3, 0.72, 0.25, 23, 55),
]
_NKANGALA_CALM = [
    (3, 3, 0.6, 0.28, 25, 50), (2, 2, 0.6, 0.27, 26, 48), (1, 4, 0.65, 0.29, 25, 52),
]
_NKANGALA_NOVEL = (0, 640, 0.7, 0.30, 25, 50)  # 640mm/24h is far outside the plausible envelope


def build_demo_history() -> list[WeatherReading]:
    """Ordered oldest-first for ingestion; the last item inserted lands highest in the
    dashboard's newest-first feed, so the eThekwini critical alert is deliberately last."""
    out: list[WeatherReading] = []
    for days_ago, rain, river, soil, temp, hum in _UMGUNGUNDLOVU:
        out.append(_reading("KZN-UMGUNGUNDLOVU", "SAWS-PMB-SEED", days_ago, rain, river, soil, temp, hum))
    for days_ago, rain, river, soil, temp, hum in _KINGCETSHWAYO:
        out.append(_reading("KZN-KINGCETSHWAYO", "SAWS-RBB-SEED", days_ago, rain, river, soil, temp, hum))
    for days_ago, rain, river, soil, temp, hum in _NKANGALA_CALM:
        out.append(_reading("MP-NKANGALA", "SAWS-WBK-SEED", days_ago, rain, river, soil, temp, hum))
    out.append(_reading("MP-NKANGALA", "SAWS-WBK-SEED", *_NKANGALA_NOVEL))
    for days_ago, rain, river, soil, temp, hum in _EHLANZENI:
        out.append(_reading("MP-EHLANZENI", "SAWS-MBB-SEED", days_ago, rain, river, soil, temp, hum))
    for days_ago, rain, river, soil, temp, hum in _ETHEKWINI:
        out.append(_reading("KZN-ETHEKWINI", "SAWS-DBN-SEED", days_ago, rain, river, soil, temp, hum))
    return out