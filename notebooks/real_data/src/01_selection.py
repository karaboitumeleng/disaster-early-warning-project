# %% [markdown]
# # 01 - Selection (KDD stage 1) - real data
# **Disaster Early Warning project - machine learning on the two real weather files in this repo.**
#
# This notebook series (01-05) is the *real-data* counterpart of the synthetic pipeline in
# `backend/notebooks`. Every number below is computed from the two Excel files in the repo root:
#
# | File | Source | Location | Period |
# |---|---|---|---|
# | `durban_kzn_daily_2021-2022.xlsx` | Open-Meteo Historical Weather API (reanalysis) | Durban, KwaZulu-Natal | 2021-06-01 to 2022-06-30 |
# | `mbombela_mpumalanga_daily_2021-2022.csv.xlsx` | Open-Meteo Historical Weather API (reanalysis) | Mbombela, Mpumalanga | 2021-06-01 to 2022-06-30 |
#
# **What this data is not:** it holds daily weather only. There are no river levels, no satellite tiles and
# no recorded flood events in these files, so the CNN-LSTM in the backend cannot be trained on it.
# Notebook 03 therefore builds a rainfall-hazard target from the data itself and says so openly.

# %%
import sys
from pathlib import Path


def _find_helpers():
    for base in [Path.cwd(), *Path.cwd().parents]:
        for cand in (base, base / "notebooks" / "real_data"):
            if (cand / "weather_data.py").is_file():
                return cand
    raise SystemExit("weather_data.py not found. Open this notebook from inside the repository.")


sys.path.insert(0, str(_find_helpers()))

import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import weather_data as wd

ROOT = wd.find_root()
OUT = wd.out_dir(ROOT)
FIG = OUT / "figures"
FIG.mkdir(exist_ok=True)
COLORS = {"KZN-ETHEKWINI": "#2a6fbb", "MP-EHLANZENI": "#d9822b"}
LABEL = {rid: s["label"] for rid, s in wd.STATIONS.items()}
plt.rcParams.update({"figure.dpi": 100, "axes.spines.top": False, "axes.spines.right": False})
print("repo root:", ROOT)

# %% [markdown]
# ## 1. Load the files
# The Excel sheets store the CSV text in one column (a metadata block, a blank line, then the table).
# `weather_data.load_station` parses that layout and raises an error if it is not what it expects.

# %%
df, meta = wd.load_all(ROOT)
pd.DataFrame(meta).T[["label", "lat", "lon", "elevation_m", "file"]]

# %%
df.head()

# %% [markdown]
# ## 2. Coverage and integrity checks

# %%
rows = []
for rid, g in df.groupby("region_id"):
    expected = pd.date_range(g["date"].min(), g["date"].max(), freq="D")
    rows.append({
        "region": LABEL[rid], "rows": len(g), "first_day": g["date"].min().date(),
        "last_day": g["date"].max().date(), "calendar_days_expected": len(expected),
        "missing_days": len(expected.difference(g["date"])), "duplicate_days": int(g["date"].duplicated().sum()),
        "missing_values": int(g.isna().sum().sum()),
    })
pd.DataFrame(rows)

# %% [markdown]
# Both files cover 395 consecutive days with no gaps and no missing values. (`Dataset_README.md` says
# 399 days; that figure appears to count the four header lines of each file. The rows are the truth.)

# %% [markdown]
# ## 3. First look at the variables

# %%
summary = df.groupby("region_id")[["rainfall_mm", "temperature_c", "humidity_pct", "pressure_hpa", "wind_kmh"]] \
    .describe().T.round(2)
summary

# %%
wet = []
for rid, g in df.groupby("region_id"):
    top = g.nlargest(5, "rainfall_mm")[["date", "rainfall_mm"]].assign(region=LABEL[rid])
    wet.append(top)
wettest = pd.concat(wet, ignore_index=True)
wettest["date"] = wettest["date"].dt.date
wettest

# %% [markdown]
# Durban's wettest day in this file is **2022-05-21 (117.8 mm)**; 2022-04-11 (100.7 mm), the day linked to the
# April 2022 KwaZulu-Natal floods, is second, and 2022-05-22 (93.7 mm) is third. `Dataset_README.md` names
# 2022-04-11 as the wettest day - the data shows a slightly different order.

# %%
fig, axes = plt.subplots(2, 1, figsize=(11, 6), sharex=True)
for ax, (rid, g) in zip(axes, df.groupby("region_id")):
    ax.bar(g["date"], g["rainfall_mm"], width=1.0, color=COLORS[rid])
    top = g.nlargest(3, "rainfall_mm")
    for _, r in top.iterrows():
        ax.annotate(f"{r['date']:%d %b %Y}\n{r['rainfall_mm']:.0f} mm", (r["date"], r["rainfall_mm"]),
                    textcoords="offset points", xytext=(-6, 4), ha="right", fontsize=8)
    ax.set_title(LABEL[rid], loc="left", fontsize=11)
    ax.set_ylabel("daily rainfall (mm)")
fig.suptitle("Daily rainfall, June 2021 - June 2022 (Open-Meteo reanalysis)", y=0.99)
fig.tight_layout()
fig.savefig(FIG / "01_daily_rainfall.png", dpi=130)
plt.show()

# %%
monthly = (df.assign(month=df["date"].dt.to_period("M").astype(str))
             .pivot_table(index="month", columns="region_id", values="rainfall_mm", aggfunc="sum")
             .rename(columns=LABEL).round(1))
ax = monthly.plot(kind="bar", figsize=(10, 3.8), color=[COLORS[r] for r in COLORS], width=0.8)
ax.set_ylabel("monthly rainfall (mm)")
ax.set_xlabel("")
ax.set_title("Monthly rainfall totals: a clear summer-rainfall season", loc="left")
plt.tight_layout()
plt.savefig(FIG / "01_monthly_rainfall.png", dpi=130)
plt.show()
monthly

# %% [markdown]
# ## 4. Record what was selected (with checksums)
# The checksums let a reader confirm later that the notebooks ran on exactly these files.

# %%
df.to_csv(OUT / "weather_selected.csv", index=False)
wd_info = {"data_kind": "real", "source": "Open-Meteo Historical Weather API (reanalysis)",
           "rows": int(len(df)), "stations": meta}
(OUT / "weather_selected.meta.json").write_text(json.dumps(wd_info, indent=2, default=str), encoding="utf-8")
print("saved", OUT.relative_to(ROOT) / "weather_selected.csv", df.shape)
{rid: m["sha256"][:16] + "..." for rid, m in meta.items()}
