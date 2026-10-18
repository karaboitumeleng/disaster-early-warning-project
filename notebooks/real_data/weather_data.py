"""Helpers for the real-data notebooks (the two Open-Meteo Excel files in the repo root).

The .xlsx files are CSV text pasted into a single column: two metadata lines, a blank line,
a header line, then one row per day. `load_station` parses that layout explicitly and fails
loudly if it is not what we expect."""
from __future__ import annotations

import hashlib
import io
import re
from pathlib import Path

import pandas as pd

SEED = 42

# region ids follow the project's REGIONS table (notebooks/common.py)
STATIONS = {
    "KZN-ETHEKWINI": {"label": "Durban (KwaZulu-Natal)", "file": "durban_kzn_daily_2021-2022.xlsx"},
    "MP-EHLANZENI": {"label": "Mbombela (Mpumalanga)", "file": "mbombela_mpumalanga_daily_2021-2022.csv.xlsx"},
}

# Open-Meteo column (units stripped) -> standard name used in the notebooks
COLUMN_MAP = {
    "time": "date",
    "rain_sum": "rainfall_mm",
    "temperature_2m_mean": "temperature_c",
    "relative_humidity_2m_mean": "humidity_pct",
    "pressure_msl_mean": "pressure_hpa",
    "wind_speed_10m_max": "wind_kmh",
}

# Physically plausible limits, used as a check only (nothing is clipped).
BOUNDS = {
    "rainfall_mm": (0, 1000), "temperature_c": (-20, 55), "humidity_pct": (0, 100),
    "pressure_hpa": (850, 1100), "wind_kmh": (0, 300),
}

OUT_DIRNAME = "outputs"


class DataError(Exception):
    """The input file is not in the expected layout."""


def find_root(start: Path | None = None) -> Path:
    """Repo root = the nearest parent folder that contains the station files."""
    sentinel = STATIONS["KZN-ETHEKWINI"]["file"]
    here = Path(start or Path.cwd()).resolve()
    for p in [here, *here.parents]:
        if (p / sentinel).is_file():
            return p
    raise DataError(f"{sentinel} not found in {here} or any parent folder. "
                    "Open the notebook from inside the repository.")


def out_dir(root: Path) -> Path:
    d = root / "notebooks" / "real_data" / OUT_DIRNAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_station(path: Path) -> tuple[pd.DataFrame, dict]:
    """Return (daily dataframe with standard column names, metadata dict)."""
    raw = pd.read_excel(path, header=None, dtype=str)
    if raw.shape[1] != 1:
        raise DataError(f"{path.name}: expected everything in one column, found {raw.shape[1]}")
    lines = raw[0].dropna().astype(str).tolist()
    if len(lines) < 4 or not lines[0].startswith("latitude"):
        raise DataError(f"{path.name}: metadata block not found")
    lat, lon, elev = (float(v) for v in lines[1].split(",")[:3])
    head = next((i for i, ln in enumerate(lines) if ln.startswith("time,")), None)
    if head is None:
        raise DataError(f"{path.name}: header line starting with 'time,' not found")
    df = pd.read_csv(io.StringIO("\n".join(lines[head:])))
    df.columns = [re.sub(r"\s*\(.*\)$", "", c).strip() for c in df.columns]  # drop units (and the mojibake in them)
    missing = set(COLUMN_MAP) - set(df.columns)
    if missing:
        raise DataError(f"{path.name}: missing columns {sorted(missing)}; found {list(df.columns)}")
    df = df.rename(columns=COLUMN_MAP)[list(COLUMN_MAP.values())]
    df["date"] = pd.to_datetime(df["date"], format="%Y-%m-%d")
    for c in df.columns.drop("date"):
        df[c] = pd.to_numeric(df[c], errors="raise")
    return df, {"lat": lat, "lon": lon, "elevation_m": elev}


def load_all(root: Path) -> tuple[pd.DataFrame, dict]:
    """Both stations stacked into one long dataframe with a region_id column."""
    frames, meta = [], {}
    for rid, spec in STATIONS.items():
        df, m = load_station(root / spec["file"])
        df.insert(0, "region_id", rid)
        frames.append(df)
        meta[rid] = {**m, "label": spec["label"], "file": spec["file"],
                     "sha256": sha256_file(root / spec["file"])}
    return pd.concat(frames, ignore_index=True), meta
