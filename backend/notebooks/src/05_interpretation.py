# %% [markdown]
# # 05 - Interpretation (KDD stage 5)
# Evaluate against the SMART objectives and write the model card.

# %%
import json
import sys
from pathlib import Path

try:
    ROOT = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p / "notebooks" / "common.py").exists())
except StopIteration:
    raise SystemExit("notebooks/common.py not found. Run inside the repo.")
sys.path.insert(0, str(ROOT / "notebooks"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import roc_curve

m = json.loads((ROOT / "models" / "metrics.json").read_text())
preds = np.load(ROOT / "models" / "test_predictions.npz")
fig_dir = ROOT / "docs" / "figures"
fig_dir.mkdir(parents=True, exist_ok=True)

table = pd.DataFrame({k: {a: b for a, b in v.items() if a != "confusion_matrix"}
                      for k, v in m["models"].items()}).T.round(3)
print(table)

# %%
TARGET = 0.80
yt = preds["y"]
print(f"Always-predict-'no flood' accuracy on the test split: {1 - yt.mean():.3f}  (why accuracy alone misleads)")
for name, v in m["models"].items():
    verdict = "meets" if v["accuracy"] >= TARGET else "MISSES"
    print(f"{name:18s} accuracy={v['accuracy']:.3f} balanced_acc={v['balanced_accuracy']:.3f} "
          f"F1={v['f1']:.3f} AUC={v['roc_auc']:.3f} -> {verdict} the {TARGET:.0%} accuracy target")
if m["data_kind"] != "real":
    print("\nWARNING: metrics come from SYNTHETIC data. They validate the pipeline, not the project objective.")

# %%
fig, axes = plt.subplots(1, len(m["models"]), figsize=(4 * len(m["models"]), 3.6))
for ax, (name, v) in zip(np.atleast_1d(axes), m["models"].items()):
    cm = np.array(v["confusion_matrix"])
    ax.imshow(cm, cmap="Blues")
    for (i, j), val in np.ndenumerate(cm):
        ax.text(j, i, str(val), ha="center", va="center", fontsize=12)
    ax.set_xticks([0, 1], ["no flood", "flood"])
    ax.set_yticks([0, 1], ["no flood", "flood"])
    ax.set_xlabel("predicted")
    ax.set_ylabel("actual")
    ax.set_title(name)
fig.tight_layout()
fig.savefig(fig_dir / "confusion_matrices.png", dpi=130)

plt.figure(figsize=(5, 4))
for name in m["models"]:
    fpr, tpr, _ = roc_curve(yt, preds[name])
    plt.plot(fpr, tpr, label=f"{name} (AUC {m['models'][name]['roc_auc']:.3f})")
plt.plot([0, 1], [0, 1], "k--", lw=0.8)
plt.xlabel("false positive rate")
plt.ylabel("true positive rate")
plt.legend()
plt.tight_layout()
plt.savefig(fig_dir / "roc.png", dpi=130)

# %%
p = m["primary"]
card = f"""# Model card - EWSA flood risk (hybrid CNN-LSTM)

- **Data kind:** {m['data_kind']} (dataset SHA-256: {json.dumps(m['dataset_sha256'])})
- **Intended use:** decision support for NDMC officers. Not a substitute for official SAWS warnings.
- **Architecture:** CNN over 4-channel 16x16 tiles + LSTM over a 14-day window, fused MLP head.
- **Seed:** {m['seed']}
- **Hyperparameters:** {json.dumps(m['hyperparameters'])}
- **Primary model test metrics:** {json.dumps({k: round(v, 3) for k, v in m['models'][p].items() if k != 'confusion_matrix'})}
- **Baselines:** {', '.join(k for k in m['models'] if k != p)}
- **Uncertainty:** MC-dropout std {m['uncertainty']['mc_dropout_mean_std']:.3f} (not a calibrated interval).
- **Novelty detector:** autoencoder; flags {m['novelty']['flag_rate_test']:.1%} of test rows, {m['novelty']['flag_rate_shifted']:.1%} of shifted rows.

## Limitations
- If data kind is synthetic, these numbers say nothing about real-world performance.
- Single hazard (flood) only; no disaster-type classification yet.
- Not yet loaded by the API: the live alert path uses the statistical baseline predictor.
"""
(ROOT / "models" / "model_card.md").write_text(card, encoding="utf-8")
print("wrote models/model_card.md")
