# Performance evidence

This file is a template. Do not treat any number as measured until you have pasted your own
output below. Nothing here has been run.

## 1. Alert latency (objective: under 60 seconds, ingest to alert)

Procedure:
1. Start the API (`make run`) with `.env` configured.
2. `set DEMO_PASSWORD=<value>` then `make demo` (runs scripts/measure_latency.py).
3. Repeat at least 20 times with distinct station IDs; record client-observed seconds and the
   server-side `latency_ms` from each alert (also shown on the dashboard Model page).

| Run date | Machine | Runs | Client-observed p50 / max (s) | Server latency p95 / max (ms) |
|---|---|---|---|---|
| (fill in) | (fill in) | (fill in) | (fill in) | (fill in) |

Caveat: the current alert path uses the statistical baseline predictor. Re-measure after the
CNN-LSTM is wired in; CNN inference on precomputed tiles is expected to dominate the cost.

## 2. Model accuracy (objective: at least 80%)

Source of truth: `notebooks/05_interpretation.ipynb` and `models/metrics.json` after
`python scripts/train_all.py`.

| Model | Data kind | Accuracy | Balanced acc. | F1 | ROC-AUC |
|---|---|---|---|---|---|
| (fill in) | synthetic / real | | | | |

Rules for claiming the objective:
- Only real data (SAWS, Sentinel-2/Landsat, EM-DAT) counts. Synthetic results validate the pipeline only.
- Report accuracy together with balanced accuracy and F1. With rare floods, an always-"no flood"
  predictor already scores high accuracy.
- Splits are chronological; the test split is used once.
