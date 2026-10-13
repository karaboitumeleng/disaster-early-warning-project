"""Shared helpers for the KDD notebooks: seeds, hashing, and a SYNTHETIC data generator.

The generator exists so the pipeline runs end-to-end offline. Its labels are a formula plus
noise, so model scores on it validate the code, NOT the project's accuracy objective."""
from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
TILE = 16
# id: (lat, lon, flood susceptibility 0-1, impervious fraction 0-1). The last two stand in
# for terrain/SANLC-derived statics until real layers are wired in.
REGIONS = {
    "KZN-ETHEKWINI": (-29.86, 31.02, 0.85, 0.55),
    "KZN-ILEMBE": (-29.33, 31.29, 0.70, 0.30),
    "KZN-UGU": (-30.74, 30.45, 0.75, 0.20),
    "KZN-UMGUNGUNDLOVU": (-29.60, 30.38, 0.55, 0.25),
    "KZN-UTHUKELA": (-28.56, 29.78, 0.50, 0.15),
    "KZN-KING-CETSHWAYO": (-28.78, 32.04, 0.65, 0.25),
    "MP-EHLANZENI": (-25.47, 30.98, 0.60, 0.20),
    "MP-GERT-SIBANDE": (-26.53, 29.98, 0.35, 0.15),
    "MP-NKANGALA": (-25.77, 29.46, 0.40, 0.25),
}


def set_seed(seed: int = SEED) -> None:
    random.seed(seed)
    np.random.seed(seed)
    try:
        import torch

        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
    except ImportError:
        pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_meta(path: Path, **info) -> None:
    path.write_text(json.dumps(info, indent=2, default=str), encoding="utf-8")


def generate_synthetic(years: int = 4, seed: int = SEED) -> tuple[pd.DataFrame, np.ndarray]:
    """Daily weather/hydrology per region + 4-channel 16x16 'satellite' tiles (SYNTHETIC)."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2019-01-01", periods=365 * years, freq="D")
    n = len(dates)
    season = np.cos(2 * np.pi * (dates.dayofyear.to_numpy() - 15) / 365)  # summer-rainfall peak
    frames, tile_blocks = [], []
    for rid, (lat, lon, susc, imperv) in REGIONS.items():
        rain = np.where(rng.random(n) < 0.12 + 0.10 * season, rng.gamma(1.5, 14.0, n), 0.0)
        rain = rain + np.where(rng.random(n) < 0.006, rng.uniform(80, 220, n), 0.0)
        api = np.zeros(n)
        api[0] = rain[0]
        for t in range(1, n):
            api[t] = 0.85 * api[t - 1] + rain[t]
        soil = np.clip(1 - np.exp(-api / 60.0), 0, 1)
        river = np.clip(0.4 + 0.035 * api * (0.4 + susc) + rng.normal(0, 0.15, n), 0, None)
        temp = 21 + 5 * season - 0.02 * rain + rng.normal(0, 1.5, n)
        hum = np.clip(55 + 0.2 * np.minimum(rain, 100) + 15 * soil + rng.normal(0, 4, n), 5, 100)
        pres = 1013 - 0.04 * rain + rng.normal(0, 3, n)
        wind = rng.gamma(2.0, 2.5, n)
        z = -5.2 + 0.03 * api * (0.5 + susc) + 0.015 * rain * imperv + rng.normal(0, 0.5, n)
        event = (rng.random(n) < 1 / (1 + np.exp(-z))).astype(np.int8)
        frames.append(pd.DataFrame({
            "region_id": rid, "date": dates, "lat": lat, "lon": lon,
            "rainfall_mm": rain, "river_level_m": river, "temperature_c": temp,
            "humidity_pct": hum, "pressure_hpa": pres, "wind_ms": wind, "soil_moisture": soil,
            "susceptibility_idx": susc, "impervious_frac": imperv, "event": event,
        }))
        base = np.stack([np.kron(rng.normal(size=(4, 4)), np.ones((4, 4))) for _ in range(4)])
        wet = (0.6 * soil * (0.4 + susc))[:, None, None]
        tiles = np.empty((n, 4, TILE, TILE), dtype=np.float32)
        tiles[:, 0] = 0.2 * base[0] + wet + rng.normal(0, 0.05, (n, TILE, TILE))       # NDWI-like
        tiles[:, 1] = 0.2 * base[1] - 0.5 * wet + rng.normal(0, 0.05, (n, TILE, TILE))  # NDVI-like
        tiles[:, 2] = 0.2 * base[2] + 0.3 * wet + rng.normal(0, 0.05, (n, TILE, TILE))  # SWIR-like
        tiles[:, 3] = 0.3 * base[3] - susc + rng.normal(0, 0.02, (n, TILE, TILE))       # elevation
        tile_blocks.append(tiles)
    df = pd.concat(frames, ignore_index=True)
    df.insert(0, "row_id", np.arange(len(df)))
    return df, np.concatenate(tile_blocks)


def inject_gaps(df: pd.DataFrame, seed: int = SEED, frac: float = 0.03, max_run: int = 6):
    """Simulate sensor outages (runs of NaN) in non-rainfall sensor columns."""
    rng = np.random.default_rng(seed)
    df = df.copy()
    for col in ("river_level_m", "soil_moisture", "humidity_pct"):
        j = df.columns.get_loc(col)
        for s in rng.integers(0, len(df), int(len(df) * frac / 3)):
            df.iloc[s : s + int(rng.integers(1, max_run + 1)), j] = np.nan
    return df
