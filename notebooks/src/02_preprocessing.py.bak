# %% [markdown]
# # 02 - Preprocessing (KDD stage 2)
# Data-gap strategy (proposal risk mitigation):
# 1. add an explicit **missingness indicator** per gappy sensor column,
# 2. **interpolate** short gaps (<= 3 days) within each region,
# 3. fill longer gaps with the region median (the indicator tells the model it is a fill),
# 4. never interpolate rainfall (an unknown rainfall value cannot be inferred from neighbours).

# %%
import sys
from pathlib import Path

try:
    ROOT = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p / "notebooks" / "common.py").exists())
except StopIteration:
    raise SystemExit("notebooks/common.py not found. Run inside the repo.")
sys.path.insert(0, str(ROOT / "notebooks"))

import pandas as pd
from common import inject_gaps, set_seed, sha256_file, write_meta

set_seed()
df = pd.read_csv(ROOT / "data" / "ewsa_selected.csv", parse_dates=["date"])
df = inject_gaps(df)  # SYNTHETIC ONLY: simulate sensor outages
print(df.isna().mean().round(4)[lambda s: s > 0])

# %%
GAP_COLS = ["river_level_m", "soil_moisture", "humidity_pct"]
df = df.sort_values(["region_id", "date"]).reset_index(drop=True)
for c in GAP_COLS:
    df[f"{c}_missing"] = df[c].isna().astype(int)
    df[c] = df.groupby("region_id")[c].transform(lambda s: s.interpolate(limit=3, limit_direction="both"))
    df[c] = df[c].fillna(df.groupby("region_id")[c].transform("median"))
assert df[GAP_COLS].isna().sum().sum() == 0
print(df[[f"{c}_missing" for c in GAP_COLS]].mean().round(4))

# %%
RANGES = {"rainfall_mm": (0, 1000), "river_level_m": (0, 50), "soil_moisture": (0, 1),
          "temperature_c": (-20, 55), "humidity_pct": (0, 100), "pressure_hpa": (850, 1100),
          "wind_ms": (0, 80)}
for col, (lo, hi) in RANGES.items():
    bad = int(((df[col] < lo) | (df[col] > hi)).sum())
    print(f"{col:15s} out-of-range rows: {bad}")
    df[col] = df[col].clip(lo, hi)

out = ROOT / "data" / "ewsa_clean.csv"
df.to_csv(out, index=False)
write_meta(ROOT / "data" / "ewsa_clean.meta.json", data_kind="synthetic",
           rows=len(df), sha256={out.name: sha256_file(out)})
print("saved", out.name, df.shape)
