# %% [markdown]
# # 01 - Selection (KDD stage 1)
# Choose and document the data. Target: flood risk for KZN and Mpumalanga districts.
#
# | Source | Role | Status in this notebook |
# |---|---|---|
# | Sentinel-2 / Landsat 8 | spatial features (CNN) | SYNTHETIC tiles |
# | SAWS stations | rainfall, river level, T, RH, pressure, wind (LSTM) | SYNTHETIC |
# | PSMSL tide gauges | coastal sea level | not yet used |
# | SANLC | land-cover statics | stand-in columns |
# | EM-DAT / DesInventar | event labels | SYNTHETIC labels |
#
# **Important:** results computed on synthetic data validate the pipeline only. See docs/DATA_SOURCES.md.

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
from common import REGIONS, SEED, generate_synthetic, set_seed, sha256_file, write_meta

set_seed()
(ROOT / "data").mkdir(exist_ok=True)

# %%
raw = ROOT / "data" / "raw"
real_files = sorted(raw.glob("*")) if raw.exists() else []
print("Real raw files found:", [f.name for f in real_files] or "none")
USE_SYNTHETIC = True  # set False only after real loaders are written below
if not USE_SYNTHETIC:
    raise NotImplementedError("Write loaders for the files in data/raw (see docs/DATA_SOURCES.md).")

# %%
df, tiles = generate_synthetic(years=4, seed=SEED)
csv_path = ROOT / "data" / "ewsa_selected.csv"
tile_path = ROOT / "data" / "ewsa_tiles.npz"
df.to_csv(csv_path, index=False)
np.savez_compressed(tile_path, tiles=tiles)
write_meta(
    ROOT / "data" / "ewsa_selected.meta.json",
    data_kind="synthetic", seed=SEED, rows=len(df), regions=list(REGIONS),
    sha256={csv_path.name: sha256_file(csv_path), tile_path.name: sha256_file(tile_path)},
)
print(df.shape, tiles.shape)
print("Flood-day prevalence:", round(float(df["event"].mean()), 4))
assert 0.005 < df["event"].mean() < 0.30, "prevalence outside sane range"
