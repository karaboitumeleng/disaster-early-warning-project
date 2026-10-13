# %% [markdown]
# # 03 - Transformation (KDD stage 3)
# * antecedent precipitation index (API, decay 0.85) from cleaned rainfall
# * 14-day lookback windows per region (LSTM input)
# * satellite tile at the window's last day (CNN input)
# * **chronological** split by date (no random shuffling: avoids temporal leakage)
# * scalers fitted on the training split only
# * target: flood event on the day AFTER the window ends

# %%
import json
import sys
from pathlib import Path

try:
    ROOT = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p / "notebooks" / "common.py").exists())
except StopIteration:
    raise SystemExit("notebooks/common.py not found. Run inside the repo.")
sys.path.insert(0, str(ROOT / "notebooks"))

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view
from common import set_seed, sha256_file, write_meta

set_seed()
df = (pd.read_csv(ROOT / "data" / "ewsa_clean.csv", parse_dates=["date"])
        .sort_values(["region_id", "date"]).reset_index(drop=True))
tiles_all = np.load(ROOT / "data" / "ewsa_tiles.npz")["tiles"]


def api_series(rain: np.ndarray, k: float = 0.85) -> np.ndarray:
    out = np.zeros_like(rain, dtype=float)
    out[0] = rain[0]
    for t in range(1, len(rain)):
        out[t] = k * out[t - 1] + rain[t]
    return out


df["api"] = df.groupby("region_id")["rainfall_mm"].transform(
    lambda s: pd.Series(api_series(s.to_numpy()), index=s.index))

# %%
L = 14
FEATS = ["rainfall_mm", "river_level_m", "temperature_c", "humidity_pct", "pressure_hpa",
         "wind_ms", "soil_moisture", "api", "river_level_m_missing", "soil_moisture_missing",
         "susceptibility_idx", "impervious_frac"]
seqs, tls, ys, dts, regs = [], [], [], [], []
for rid, g in df.groupby("region_id", sort=True):
    g = g.reset_index(drop=True)
    n = len(g)
    arr = g[FEATS].to_numpy(dtype=np.float32)
    win = sliding_window_view(arr, L, axis=0).transpose(0, 2, 1)[: n - L]  # (n-L, L, F)
    end = np.arange(L - 1, n - 1)
    seqs.append(win)
    ys.append(g["event"].to_numpy()[end + 1])
    dts.append(g["date"].to_numpy()[end])
    regs.append(np.full(len(end), rid))
    tls.append(tiles_all[g["row_id"].to_numpy()[end]])
X, T = np.concatenate(seqs), np.concatenate(tls)
y, dates, region = np.concatenate(ys).astype(np.float32), np.concatenate(dts), np.concatenate(regs)
print(X.shape, T.shape, y.shape)

# %%
tr = dates < np.datetime64("2021-07-01")
va = (dates >= np.datetime64("2021-07-01")) & (dates < np.datetime64("2022-04-01"))
te = dates >= np.datetime64("2022-04-01")
for name, m in (("train", tr), ("val", va), ("test", te)):
    print(f"{name:5s} n={m.sum():6d} positives={int(y[m].sum()):4d} prevalence={y[m].mean():.3f}")
assert y[te].sum() >= 20, "too few test positives for stable metrics"

F = X.shape[2]
mean = X[tr].reshape(-1, F).mean(0)
std = X[tr].reshape(-1, F).std(0) + 1e-6
Xs = ((X - mean) / std).astype(np.float32)
tmean = T[tr].mean(axis=(0, 2, 3), keepdims=True)[0]
tstd = T[tr].std(axis=(0, 2, 3), keepdims=True)[0] + 1e-6
Ts = ((T - tmean) / tstd).astype(np.float32)

rain_i = FEATS.index("rainfall_mm")
tab = np.concatenate([Xs[:, -1, :], Xs[:, -3:, rain_i].sum(1, keepdims=True),
                      Xs[:, -7:, rain_i].sum(1, keepdims=True)], axis=1).astype(np.float32)

# %%
arrays = {}
for name, m in (("train", tr), ("val", va), ("test", te)):
    arrays[f"seq_{name}"], arrays[f"tile_{name}"] = Xs[m], Ts[m]
    arrays[f"tab_{name}"], arrays[f"y_{name}"] = tab[m], y[m]
    arrays[f"date_{name}"] = dates[m].astype("datetime64[D]").astype(str)
    arrays[f"region_{name}"] = region[m]
out = ROOT / "data" / "ewsa_dataset_v1.npz"
np.savez_compressed(out, **arrays)

(ROOT / "models").mkdir(exist_ok=True)
prep = {"lookback": L, "features": FEATS, "seq_mean": mean.tolist(), "seq_std": std.tolist(),
        "tile_mean": tmean.ravel().tolist(), "tile_std": tstd.ravel().tolist(),
        "api_decay": 0.85, "splits": {"train": "< 2021-07-01", "val": "2021-07-01..2022-03-31",
                                      "test": ">= 2022-04-01"}}
(ROOT / "models" / "preprocessing.json").write_text(json.dumps(prep, indent=2), encoding="utf-8")
write_meta(ROOT / "data" / "ewsa_dataset_v1.meta.json", data_kind="synthetic",
           sha256={out.name: sha256_file(out), "ewsa_clean.csv": sha256_file(ROOT / "data" / "ewsa_clean.csv")})
print("saved", out.name)
