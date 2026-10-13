"""Real-data loaders for notebook 01 (config-driven; nothing here knows your file formats).

Layout under data/raw/ (never commit; licences apply):
  sources.json            copy of notebooks/sources.example.json, edited to match YOUR files
  manifest.json           SHA-256 of every input file (python notebooks/loaders.py manifest data/raw)
  <files named in sources.json>, tiles/<REGION_ID>/<YYYY-MM-DD>.npy|.tif

build_real_dataset() returns the same schema the synthetic generator produces, so notebooks
02-05 run unchanged. Every fill, proxy and drop is recorded in the returned `info` dict."""
from __future__ import annotations

import calendar
import json
import re
import sys
import warnings
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from common import sha256_file

TILE, N_BANDS = 16, 4
TILE_EXT = (".npy", ".tif", ".tiff")
STD_COLS = ["rainfall_mm", "river_level_m", "temperature_c", "humidity_pct", "pressure_hpa", "wind_ms"]
EXTRA_COLS = ["tmax_c", "tmin_c"]
BOUNDS = {
    "rainfall_mm": (0, 1000), "river_level_m": (0, 50), "temperature_c": (-20, 55),
    "tmax_c": (-20, 55), "tmin_c": (-20, 55), "humidity_pct": (0, 100),
    "pressure_hpa": (850, 1100), "wind_ms": (0, 80),
}
DEFAULTS = {"temperature_c": 20.0, "humidity_pct": 65.0, "pressure_hpa": 1013.0, "wind_ms": 3.0}
_ID = re.compile(r"^[A-Za-z0-9_-]+$")


class DataError(Exception):
    """Bad or unverifiable input data. Messages say what to fix."""


# ---------------------------------------------------------------- integrity / config
def _resolve(raw_dir: Path, rel: str) -> Path:
    root = Path(raw_dir).resolve()
    p = (root / rel).resolve()
    if not p.is_relative_to(root):
        raise DataError(f"path escapes data/raw: {rel}")
    if not p.exists():
        raise DataError(f"file not found: {rel}")
    return p


def write_manifest(raw_dir: Path) -> dict[str, str]:
    root = Path(raw_dir).resolve()
    out: dict[str, str] = {}
    for f in sorted(root.rglob("*")):
        if f.is_file() and f.name != "manifest.json" and not f.name.startswith("sources") \
                and f.name.lower() != "readme.md":
            out[f.relative_to(root).as_posix()] = sha256_file(f)
    (root / "manifest.json").write_text(json.dumps(out, indent=2, sort_keys=True), encoding="utf-8")
    return out


def verify_manifest(raw_dir: Path, files: list[Path]) -> dict[str, str]:
    root = Path(raw_dir).resolve()
    mpath = root / "manifest.json"
    if not mpath.is_file():
        raise DataError("data/raw/manifest.json missing. After reviewing your files run: "
                        "python notebooks/loaders.py manifest data/raw")
    manifest = json.loads(mpath.read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    for f in files:
        rel = f.relative_to(root).as_posix()
        if rel not in manifest:
            raise DataError(f"{rel} is not listed in manifest.json (re-run the manifest command)")
        actual = sha256_file(f)
        if actual != manifest[rel]:
            raise DataError(f"checksum mismatch for {rel}: file changed since it was recorded")
        out[rel] = actual
    return out


def load_config(raw_dir: Path) -> dict[str, Any]:
    path = Path(raw_dir) / "sources.json"
    if not path.is_file():
        raise DataError("data/raw/sources.json missing (copy notebooks/sources.example.json)")
    cfg = json.loads(path.read_text(encoding="utf-8"))
    for key in ("date_range", "stations", "events", "statics", "tiles"):
        if key not in cfg:
            raise DataError(f"sources.json is missing '{key}'")
    for s in cfg["stations"]:
        for key in ("file", "region_id", "columns"):
            if key not in s:
                raise DataError(f"station entry missing '{key}': {s}")
        if not _ID.match(s["region_id"]):
            raise DataError(f"bad region_id: {s['region_id']}")
    return cfg


# ---------------------------------------------------------------- station files
def _read_table(path: Path, spec: dict[str, Any]) -> pd.DataFrame:
    na = list(spec.get("missing", ["-999", "-99", "NA", "N/A", ""]))
    if path.suffix.lower() in (".xlsx", ".xls"):
        return pd.read_excel(path, na_values=na)
    return pd.read_csv(path, na_values=na, sep=spec.get("sep", ","),
                       encoding=spec.get("encoding", "utf-8"))


def read_station_file(raw_dir: Path, spec: dict[str, Any]) -> pd.DataFrame:
    path = _resolve(raw_dir, spec["file"])
    cols: dict[str, str] = spec["columns"]
    if "date" not in cols:
        raise DataError(f"{spec['file']}: 'columns' must map 'date'")
    unknown = set(cols) - {"date", *STD_COLS, *EXTRA_COLS}
    if unknown:
        raise DataError(f"{spec['file']}: unknown standard names {sorted(unknown)}")
    raw = _read_table(path, spec)
    absent = [v for v in cols.values() if v not in raw.columns]
    if absent:
        raise DataError(f"{spec['file']}: columns not found {absent}; available: {list(raw.columns)}")
    df = pd.DataFrame()
    df["date"] = pd.to_datetime(raw[cols["date"]], format=spec.get("date_format"), errors="coerce")
    if df["date"].isna().mean() > 0.05:
        raise DataError(f"{spec['file']}: over 5% of dates unparseable (check date_format)")
    scale, offset = spec.get("scale", {}), spec.get("offset", {})
    oor: dict[str, int] = {}
    for std, src in cols.items():
        if std == "date":
            continue
        s = pd.to_numeric(raw[src], errors="coerce") * float(scale.get(std, 1.0)) \
            + float(offset.get(std, 0.0))
        lo, hi = BOUNDS[std]
        bad = (s < lo) | (s > hi)
        oor[std] = int(bad.sum())
        df[std] = s.where(~bad)  # out-of-range becomes missing, never clipped silently
    df = df.dropna(subset=["date"]).copy()
    df["date"] = df["date"].dt.normalize()
    if "temperature_c" not in df.columns and {"tmax_c", "tmin_c"} <= set(df.columns):
        df["temperature_c"] = (df["tmax_c"] + df["tmin_c"]) / 2
    df["region_id"] = spec["region_id"]
    df.attrs["out_of_range"] = oor
    return df


def _api(rain: np.ndarray, k: float = 0.85) -> np.ndarray:
    out = np.zeros_like(rain, dtype=float)
    out[0] = rain[0]
    for t in range(1, len(rain)):
        out[t] = k * out[t - 1] + rain[t]
    return out


def _daily_frame(
    raw_dir: Path, cfg: dict[str, Any], regions: list[str], start: pd.Timestamp, end: pd.Timestamp
) -> tuple[pd.DataFrame, dict[str, Any]]:
    frames = [read_station_file(raw_dir, s) for s in cfg["stations"]]
    info: dict[str, Any] = {"out_of_range": {}, "rainfall_zero_filled_days": {}, "constant_fills": {},
                            "proxies": ["soil_moisture = 1 - exp(-API/60): no soil-moisture source"]}
    for spec, f in zip(cfg["stations"], frames):
        info["out_of_range"][spec["file"]] = f.attrs.get("out_of_range", {})
    allf = pd.concat(frames, ignore_index=True)
    allf = allf[(allf["date"] >= start) & (allf["date"] <= end)]
    value_cols = [c for c in STD_COLS if c in allf.columns]
    agg = allf.groupby(["region_id", "date"], as_index=False)[value_cols].mean()  # cross-station mean
    grid = pd.date_range(start, end, freq="D")
    max_missing = float(cfg.get("max_rainfall_missing_frac", 0.05))
    out = []
    for rid in regions:
        g = agg[agg["region_id"] == rid].drop(columns=["region_id"]).set_index("date").reindex(grid)
        g.index.name = "date"
        for c in STD_COLS:
            if c not in g.columns:
                g[c] = np.nan
        n_missing = int(g["rainfall_mm"].isna().sum())
        if n_missing == len(g):
            raise DataError(f"{rid}: no rainfall data between {start.date()} and {end.date()}")
        if n_missing / len(g) > max_missing:
            raise DataError(f"{rid}: {n_missing / len(g):.1%} of days lack rainfall "
                            f"(limit {max_missing:.0%}); add stations or shorten date_range")
        if g["river_level_m"].notna().sum() == 0:
            raise DataError(f"{rid}: no river-level data. Add a hydrology file or drop the region")
        g["rainfall_mm"] = g["rainfall_mm"].fillna(0.0)  # counted below, never interpolated
        info["rainfall_zero_filled_days"][rid] = n_missing
        for c in DEFAULTS:
            g[c] = g[c].interpolate(limit=3, limit_direction="both")
        out.append(g.reset_index().assign(region_id=rid))
    df = pd.concat(out, ignore_index=True)
    for c, default in DEFAULTS.items():
        med = df[c].median()
        if pd.isna(med):
            df[c] = default
            info["constant_fills"][c] = f"no data at all; constant {default}"
            continue
        n = int(df[c].isna().sum())
        df[c] = df.groupby("region_id")[c].transform(lambda s: s.fillna(s.median())).fillna(med)
        if n:
            info["constant_fills"][c] = f"{n} rows filled with region/global median"
    return df, info


# ---------------------------------------------------------------- events (labels)
def _date_from_parts(y: Any, m: Any, d: Any, end: bool) -> pd.Timestamp | None:
    if y is None or pd.isna(y):
        return None
    try:
        y = int(y)
        m = int(m) if m is not None and not pd.isna(m) else (12 if end else 1)
        last = calendar.monthrange(y, m)[1]
        d = int(d) if d is not None and not pd.isna(d) else (last if end else 1)
        return pd.Timestamp(year=y, month=m, day=min(d, last))
    except (ValueError, OverflowError):
        return None


def load_events(
    raw_dir: Path, spec: dict[str, Any], regions: list[str], start: pd.Timestamp, end: pd.Timestamp
) -> tuple[set[tuple[str, pd.Timestamp]], dict[str, Any]]:
    raw = _read_table(_resolve(raw_dir, spec["file"]), spec)
    for col, allowed in spec.get("filter", {}).items():
        if col not in raw.columns:
            raise DataError(f"events file has no column '{col}'; available: {list(raw.columns)}")
        vals = [allowed] if isinstance(allowed, str) else list(allowed)
        raw = raw[raw[col].astype(str).str.lower().isin([str(v).lower() for v in vals])]
    s, e = spec["start"], spec["end"]
    for col in [*s.values(), *e.values(), *spec["location_columns"]]:
        if col not in raw.columns:
            raise DataError(f"events file has no column '{col}'; available: {list(raw.columns)}")
    keywords = {r: [k.lower() for k in kws] for r, kws in spec.get("region_keywords", {}).items()
                if r in regions}
    fallback = {k.lower(): [r for r in rids if r in regions]
                for k, rids in spec.get("province_fallback", {}).items()}
    max_dur = int(spec.get("max_duration_days", 7))
    pad = int(spec.get("pad_days_before", 0))
    keys: set[tuple[str, pd.Timestamp]] = set()
    matched = unmatched = skipped = 0
    examples: list[str] = []
    for _, row in raw.iterrows():
        d0 = _date_from_parts(row[s["year"]], row[s["month"]], row[s["day"]], end=False)
        d1 = _date_from_parts(row[e["year"]], row[e["month"]], row[e["day"]], end=True)
        if d0 is None:
            skipped += 1
            continue
        d1 = min(d1 if d1 is not None and d1 >= d0 else d0, d0 + pd.Timedelta(days=max_dur))
        text = " | ".join(str(row[c]) for c in spec["location_columns"]).lower()
        hit = {r for r, kws in keywords.items() if any(k in text for k in kws)}
        if not hit:
            for k, rids in fallback.items():
                if k in text:
                    hit.update(rids)
        if not hit:
            unmatched += 1
            if len(examples) < 10:
                examples.append(text[:80])
            continue
        matched += 1
        for day in pd.date_range(d0 - pd.Timedelta(days=pad), d1, freq="D"):
            if start <= day <= end:
                keys.update((r, day) for r in hit)
    info = {"matched_events": matched, "unmatched_events": unmatched, "skipped_no_date": skipped,
            "unmatched_examples": examples, "positive_region_days": len(keys)}
    return keys, info


# ---------------------------------------------------------------- statics
def read_statics(raw_dir: Path, spec: dict[str, Any], regions: list[str]) -> pd.DataFrame:
    df = _read_table(_resolve(raw_dir, spec["file"]), spec)
    need = ["region_id", "susceptibility_idx", "impervious_frac"]
    if any(c not in df.columns for c in need):
        raise DataError(f"statics file needs columns {need}; has {list(df.columns)}")
    df = df[need].drop_duplicates("region_id")
    absent = [r for r in regions if r not in set(df["region_id"])]
    if absent:
        raise DataError(f"statics file lacks regions {absent}")
    for c in need[1:]:
        if not df[c].between(0, 1).all():
            raise DataError(f"{c} must be within [0, 1]")
    return df[df["region_id"].isin(regions)]


# ---------------------------------------------------------------- tiles
def _block_mean(arr: np.ndarray, size: int) -> np.ndarray:
    rows = np.array_split(np.arange(arr.shape[0]), size)
    cols = np.array_split(np.arange(arr.shape[1]), size)
    out = np.empty((size, size), dtype=np.float32)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        for i, r in enumerate(rows):
            for j, c in enumerate(cols):
                out[i, j] = np.nanmean(arr[np.ix_(r, c)])
    return out


def _read_geotiff(path: Path) -> np.ndarray:
    try:
        import rasterio
    except ImportError as exc:
        raise DataError("reading GeoTIFF tiles needs: pip install rasterio==1.4.3") from exc
    with rasterio.open(path) as src:
        if src.count != N_BANDS:
            raise DataError(f"{path.name}: expected {N_BANDS} bands, found {src.count}")
        data = src.read(masked=True).astype("float32")
    return np.asarray(np.ma.filled(data, np.nan), dtype=np.float32)


def read_tile(path: Path, max_nan_frac: float = 0.5) -> np.ndarray | None:
    """Returns (4, 16, 16) float32, or None when the tile is too cloudy/empty to use."""
    arr = np.load(path, allow_pickle=False).astype(np.float32) if path.suffix.lower() == ".npy" \
        else _read_geotiff(path)
    if arr.ndim != 3 or arr.shape[0] != N_BANDS:
        raise DataError(f"{path.name}: expected ({N_BANDS}, H, W), got {arr.shape}")
    if arr.shape[1:] != (TILE, TILE):
        if min(arr.shape[1:]) < TILE:
            raise DataError(f"{path.name}: raster smaller than {TILE}x{TILE}")
        arr = np.stack([_block_mean(arr[b], TILE) for b in range(N_BANDS)])
    if 1.0 - float(np.isfinite(arr).mean()) > max_nan_frac:
        return None
    for b in range(N_BANDS):
        finite = np.isfinite(arr[b])
        if not finite.any():
            return None
        arr[b][~finite] = float(arr[b][finite].mean())
    return arr.astype(np.float32)


def list_tile_files(
    raw_dir: Path, spec: dict[str, Any], regions: list[str]
) -> dict[str, list[tuple[pd.Timestamp, Path]]]:
    tdir = _resolve(raw_dir, spec.get("dir", "tiles"))
    out: dict[str, list[tuple[pd.Timestamp, Path]]] = {}
    for rid in regions:
        entries: list[tuple[pd.Timestamp, Path]] = []
        rdir = tdir / rid
        if rdir.is_dir():
            for f in sorted(rdir.iterdir()):
                if f.suffix.lower() not in TILE_EXT:
                    continue
                try:
                    entries.append((pd.Timestamp(f.stem).normalize(), f))
                except ValueError as exc:
                    raise DataError(f"tile file names must be YYYY-MM-DD: {f.name}") from exc
        entries.sort(key=lambda e: e[0])
        out[rid] = entries
    return out


def align_tiles(
    df: pd.DataFrame, by_region: dict[str, tuple[np.ndarray, np.ndarray]], max_age_days: int
) -> tuple[np.ndarray, np.ndarray]:
    """Latest tile at or before each day (never a future tile); older than max_age uses the
    region's median tile and age -1."""
    usable = [t for _, tiles in by_region.values() for t in tiles]
    if not usable:
        raise DataError("no usable tiles found under data/raw/tiles/<REGION_ID>/")
    global_med = np.median(np.stack(usable), axis=0).astype(np.float32)
    out = np.empty((len(df), N_BANDS, TILE, TILE), dtype=np.float32)
    age = np.full(len(df), -1, dtype=np.int32)
    for rid, g in df.groupby("region_id"):
        idx = g.index.to_numpy()
        tdates, tiles = by_region.get(rid, (np.array([], dtype="datetime64[D]"), np.empty(0)))
        fill = np.median(tiles, axis=0).astype(np.float32) if len(tdates) else global_med
        gd = g["date"].to_numpy().astype("datetime64[D]")
        if not len(tdates):
            out[idx] = fill
            continue
        pos = np.searchsorted(tdates, gd, side="right") - 1
        for k, (i, p) in enumerate(zip(idx, pos)):
            a = int((gd[k] - tdates[p]).astype(int)) if p >= 0 else -1
            if p >= 0 and a <= max_age_days:
                out[i], age[i] = tiles[p], a
            else:
                out[i] = fill
    return out, age


# ---------------------------------------------------------------- orchestration
def build_real_dataset(
    raw_dir: Path, coords: dict[str, tuple[float, float]]
) -> tuple[pd.DataFrame, np.ndarray, dict[str, Any]]:
    raw_dir = Path(raw_dir)
    cfg = load_config(raw_dir)
    regions = sorted({s["region_id"] for s in cfg["stations"]})
    unknown = [r for r in regions if r not in coords]
    if unknown:
        raise DataError(f"regions {unknown} have no coordinates in notebooks/common.py REGIONS")
    start, end = (pd.Timestamp(x) for x in cfg["date_range"])

    tile_index = list_tile_files(raw_dir, cfg["tiles"], regions)
    files = [_resolve(raw_dir, s["file"]) for s in cfg["stations"]]
    files += [_resolve(raw_dir, cfg["events"]["file"]), _resolve(raw_dir, cfg["statics"]["file"])]
    files += [p for entries in tile_index.values() for _, p in entries]
    checksums = verify_manifest(raw_dir, files)

    df, info = _daily_frame(raw_dir, cfg, regions, start, end)
    df = df.sort_values(["region_id", "date"]).reset_index(drop=True)
    api = df.groupby("region_id")["rainfall_mm"].transform(
        lambda s: pd.Series(_api(s.to_numpy(float)), index=s.index))
    df["soil_moisture"] = (1 - np.exp(-api / 60.0)).clip(0, 1)
    df = df.merge(read_statics(raw_dir, cfg["statics"], regions), on="region_id", how="left")
    df["lat"] = df["region_id"].map(lambda r: coords[r][0])
    df["lon"] = df["region_id"].map(lambda r: coords[r][1])

    keys, ev_info = load_events(raw_dir, cfg["events"], regions, start, end)
    df["event"] = pd.MultiIndex.from_frame(df[["region_id", "date"]]).isin(list(keys)).astype("int8")
    ev_info["positive_days_by_year"] = {
        int(y): int(n) for y, n in df[df["event"] == 1].groupby(df["date"].dt.year).size().items()}
    info["events"] = ev_info

    max_nan = float(cfg["tiles"].get("max_nan_frac", 0.5))
    by_region: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    dropped = 0
    for rid, entries in tile_index.items():
        ds, ts = [], []
        for d, p in entries:
            t = read_tile(p, max_nan)
            if t is None:
                dropped += 1
                continue
            ds.append(d.to_datetime64().astype("datetime64[D]"))
            ts.append(t)
        if ts:
            by_region[rid] = (np.array(ds), np.stack(ts))
    tiles, age = align_tiles(df, by_region, int(cfg["tiles"].get("max_age_days", 15)))
    df["tile_age_days"] = age
    info["tiles"] = {"files": sum(len(v) for v in tile_index.values()), "rejected_cloudy_or_empty": dropped,
                     "rows_with_fresh_tile": int((age >= 0).sum()), "rows": len(df)}
    info["regions"], info["checksums"] = regions, checksums

    df.insert(0, "row_id", np.arange(len(df)))
    cols = ["row_id", "region_id", "date", "lat", "lon", *STD_COLS, "soil_moisture",
            "susceptibility_idx", "impervious_frac", "event", "tile_age_days"]
    df = df[cols]
    info["rows"] = int(len(df))
    return df, tiles, info


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "manifest":
        for name, digest in write_manifest(Path(sys.argv[2])).items():
            print(f"{digest}  {name}")
    else:
        sys.exit("usage: python notebooks/loaders.py manifest data/raw")
