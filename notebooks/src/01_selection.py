# %% [markdown]
# # 01 - Selection (KDD stage 1)
# Chooses and documents the data. Two modes:
# * **real**: used automatically when data/raw/sources.json exists (see docs/REAL_DATA_GUIDE.md);
#   inputs are checksum-verified against data/raw/manifest.json before use.
# * **synthetic**: offline generator, for pipeline validation ONLY.
#
# | Source | Role | Real-mode input |
# |---|---|---|
# | Sentinel-2 / Landsat 8 | spatial features (CNN) | pre-exported 4-band tiles |
# | SAWS stations | rainfall, T, RH, pressure, wind | station CSV/XLSX |
# | DWS / SAWS hydrology | river level | station CSV/XLSX |
# | SANLC + terrain | susceptibility and impervious fraction | statics CSV you supply |
# | EM-DAT / DesInventar | event labels | events export |
#
# Results computed on synthetic data validate the pipeline, not the project objective.

# %%
import sys
from pathlib import Path

try:
    ROOT = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p / "notebooks" / "common.py").exists())
except StopIteration:
    raise SystemExit("notebooks/common.py not found. Run inside the repo (on Colab: clone it first).")
sys.path.insert(0, str(ROOT / "notebooks"))

import numpy as np
import pandas as pd
import loaders
from common import REGIONS, SEED, generate_synthetic, set_seed, sha256_file, write_meta

set_seed()
(ROOT / "data").mkdir(exist_ok=True)

# %%
DATA_MODE = "auto"  # "auto" | "real" | "synthetic"
raw_dir = ROOT / "data" / "raw"
use_real = DATA_MODE == "real" or (DATA_MODE == "auto" and (raw_dir / "sources.json").is_file())
print("mode:", "REAL" if use_real else "SYNTHETIC")

# %%
if use_real:
    try:
        df, tiles, info = loaders.build_real_dataset(
            raw_dir, {k: (v[0], v[1]) for k, v in REGIONS.items()})
    except loaders.DataError as exc:
        raise RuntimeError(f"Real-data load failed: {exc}") from exc
    data_kind = "real"
else:
    df, tiles = generate_synthetic(years=4, seed=SEED)
    info, data_kind = {}, "synthetic"
print(df.shape, tiles.shape)

# %%
csv_path = ROOT / "data" / "ewsa_selected.csv"
tile_path = ROOT / "data" / "ewsa_tiles.npz"
df.to_csv(csv_path, index=False)
np.savez_compressed(tile_path, tiles=tiles)
write_meta(
    ROOT / "data" / "ewsa_selected.meta.json",
    data_kind=data_kind, seed=SEED, rows=len(df), regions=sorted(df["region_id"].unique()),
    sha256={csv_path.name: sha256_file(csv_path), tile_path.name: sha256_file(tile_path)},
    loader_info=info,
)

# Latest tile per region for the live API (data/tiles/<REGION>.npy). It is only a seed:
# nothing refreshes it yet, and real-mode tiles go stale after the training period.
tile_dir = ROOT / "data" / "tiles"
tile_dir.mkdir(exist_ok=True)
for rid, g in df.groupby("region_id"):
    last_row = int(g.sort_values("date")["row_id"].iloc[-1])
    np.save(tile_dir / f"{rid}.npy", tiles[last_row].astype(np.float32))

# %%
prev = float(df["event"].mean())
print("Flood-day prevalence:", round(prev, 5), "| positive region-days:", int(df["event"].sum()))
print(df[df["event"] == 1].groupby([df["date"].dt.year, "region_id"]).size().unstack(fill_value=0))
if data_kind == "synthetic":
    assert 0.005 < prev < 0.30, "prevalence outside sane range"
else:
    for k in ("out_of_range", "rainfall_zero_filled_days", "constant_fills", "proxies", "events", "tiles"):
        print(k, "->", info.get(k))
    if int(df["event"].sum()) < 100:
        print("WARNING: very few positive labels. Notebook 03 will likely refuse to split. "
              "Add event sources; do not lower its assertion to make it pass.")
