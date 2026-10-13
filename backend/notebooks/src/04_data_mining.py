# %% [markdown]
# # 04 - Data mining (KDD stage 4)
# Trains (a) Random Forest and Gradient Boosting baselines, (b) the hybrid CNN-LSTM, and
# (c) an autoencoder novelty detector (OWML hook). Thresholds are tuned on the validation
# split only; the test split is touched once for reporting.
#
# Note: with rare floods, plain accuracy is misleading. We report balanced accuracy, F1,
# precision, recall and ROC-AUC as well. Uncertainty is MC-dropout (NOT a calibrated interval).

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
import torch
import torch.nn as nn
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.metrics import (accuracy_score, balanced_accuracy_score, confusion_matrix, f1_score,
                             precision_score, recall_score, roc_auc_score)
from torch.utils.data import DataLoader, TensorDataset
from common import SEED, set_seed

set_seed()
MODELS = ROOT / "models"
MODELS.mkdir(exist_ok=True)
d = np.load(ROOT / "data" / "ewsa_dataset_v1.npz")
meta = json.loads((ROOT / "data" / "ewsa_dataset_v1.meta.json").read_text())
y = {s: d[f"y_{s}"].astype(int) for s in ("train", "val", "test")}


def best_threshold(yt, p):
    grid = np.linspace(0.05, 0.95, 91)
    return float(grid[int(np.argmax([f1_score(yt, (p >= t).astype(int), zero_division=0) for t in grid]))])


def evaluate(yt, p, thr):
    pred = (p >= thr).astype(int)
    return {
        "threshold": thr,
        "accuracy": float(accuracy_score(yt, pred)),
        "balanced_accuracy": float(balanced_accuracy_score(yt, pred)),
        "precision": float(precision_score(yt, pred, zero_division=0)),
        "recall": float(recall_score(yt, pred, zero_division=0)),
        "f1": float(f1_score(yt, pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(yt, p)),
        "confusion_matrix": confusion_matrix(yt, pred, labels=[0, 1]).tolist(),
    }


results, test_probs = {}, {}

# %% [markdown]
# ## Baselines (engineered tabular features)

# %%
baselines = {
    "random_forest": RandomForestClassifier(n_estimators=300, min_samples_leaf=3, n_jobs=-1,
                                            class_weight="balanced_subsample", random_state=SEED),
    "gradient_boosting": GradientBoostingClassifier(n_estimators=200, max_depth=3, random_state=SEED),
}
for name, clf in baselines.items():
    clf.fit(d["tab_train"], y["train"])
    pv, pt = clf.predict_proba(d["tab_val"])[:, 1], clf.predict_proba(d["tab_test"])[:, 1]
    results[name] = evaluate(y["test"], pt, best_threshold(y["val"], pv))
    test_probs[name] = pt
    print(name, {k: round(v, 3) for k, v in results[name].items() if k != "confusion_matrix"})

# %% [markdown]
# ## Hybrid CNN-LSTM

# %%
dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print("device:", dev)


def tt(a):
    return torch.as_tensor(a, dtype=torch.float32)


data = {s: (tt(d[f"seq_{s}"]), tt(d[f"tile_{s}"]), tt(d[f"y_{s}"])) for s in ("train", "val", "test")}


class CnnLstm(nn.Module):
    def __init__(self, n_feat, hidden=64, emb=32, p=0.3):
        super().__init__()
        self.cnn = nn.Sequential(
            nn.Conv2d(4, 16, 3, padding=1), nn.BatchNorm2d(16), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(16, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU(),
            nn.AdaptiveAvgPool2d(1), nn.Flatten(), nn.Linear(32, emb), nn.ReLU())
        self.lstm = nn.LSTM(n_feat, hidden, batch_first=True)
        self.head = nn.Sequential(nn.Dropout(p), nn.Linear(hidden + emb, 32), nn.ReLU(),
                                  nn.Dropout(p), nn.Linear(32, 1))

    def forward(self, seq, tile):
        _, (h, _) = self.lstm(seq)
        return self.head(torch.cat([h[-1], self.cnn(tile)], dim=1)).squeeze(1)


@torch.no_grad()
def logits_of(model, seq, tile, bs=512):
    model.eval()
    return torch.cat([model(seq[i:i + bs].to(dev), tile[i:i + bs].to(dev)).cpu()
                      for i in range(0, len(seq), bs)])


model = CnnLstm(n_feat=data["train"][0].shape[2]).to(dev)
pos = float(data["train"][2].sum())
neg = len(data["train"][2]) - pos
lossf = nn.BCEWithLogitsLoss(pos_weight=torch.tensor(min(neg / pos, 20.0), device=dev))
opt = torch.optim.Adam(model.parameters(), lr=1e-3, weight_decay=1e-5)
loader = DataLoader(TensorDataset(*data["train"]), batch_size=128, shuffle=True,
                    generator=torch.Generator().manual_seed(SEED))

best, best_state, patience = 1e9, None, 0
for epoch in range(25):
    model.train()
    for xs, xt, yb in loader:
        xs, xt, yb = xs.to(dev), xt.to(dev), yb.to(dev)
        opt.zero_grad()
        lossf(model(xs, xt), yb).backward()
        opt.step()
    vl = float(nn.functional.binary_cross_entropy_with_logits(
        logits_of(model, *data["val"][:2]), data["val"][2]))
    print(f"epoch {epoch + 1:2d} val_loss {vl:.4f}")
    if vl < best - 1e-4:
        best, patience = vl, 0
        best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
    else:
        patience += 1
        if patience >= 6:
            break
model.load_state_dict(best_state)

pv = torch.sigmoid(logits_of(model, *data["val"][:2])).numpy()
pt = torch.sigmoid(logits_of(model, *data["test"][:2])).numpy()
results["cnn_lstm"] = evaluate(y["test"], pt, best_threshold(y["val"], pv))
test_probs["cnn_lstm"] = pt
print("cnn_lstm", {k: round(v, 3) for k, v in results["cnn_lstm"].items() if k != "confusion_matrix"})


# %%
@torch.no_grad()
def mc_predict(model, seq, tile, n=20, bs=512):
    model.eval()
    for m in model.modules():
        if isinstance(m, nn.Dropout):
            m.train()
    runs = [torch.cat([torch.sigmoid(model(seq[i:i + bs].to(dev), tile[i:i + bs].to(dev))).cpu()
                       for i in range(0, len(seq), bs)]).numpy() for _ in range(n)]
    model.eval()
    r = np.stack(runs)
    return r.mean(0), r.std(0)


_, sd = mc_predict(model, *data["test"][:2])
uncertainty = {"mc_dropout_mean_std": float(sd.mean()), "note": "NOT a calibrated interval"}
print(uncertainty)

# %% [markdown]
# ## Novelty detector (autoencoder on tabular features)

# %%
xtr, xte = tt(d["tab_train"]), tt(d["tab_test"])
D = xtr.shape[1]
ae = nn.Sequential(nn.Linear(D, 16), nn.ReLU(), nn.Linear(16, 6), nn.ReLU(),
                   nn.Linear(6, 16), nn.ReLU(), nn.Linear(16, D))
opt_ae = torch.optim.Adam(ae.parameters(), lr=1e-3)
for _ in range(200):
    opt_ae.zero_grad()
    nn.functional.mse_loss(ae(xtr), xtr).backward()
    opt_ae.step()


@torch.no_grad()
def recon_err(x):
    ae.eval()
    return ((ae(x) - x) ** 2).mean(1).numpy()


ae_thr = float(np.quantile(recon_err(xtr), 0.99))
novelty = {
    "threshold": ae_thr,
    "flag_rate_test": float((recon_err(xte) > ae_thr).mean()),
    "flag_rate_shifted": float((recon_err(xte * 3 + 2) > ae_thr).mean()),
}
print(novelty)

# %%
torch.save(model.state_dict(), MODELS / "ewsa_cnn_lstm.pt")
torch.save(ae.state_dict(), MODELS / "autoencoder.pt")
np.savez_compressed(MODELS / "test_predictions.npz", y=y["test"], **test_probs)
doc = {
    "data_kind": meta["data_kind"], "dataset_sha256": meta["sha256"], "primary": "cnn_lstm",
    "seed": SEED, "models": results, "uncertainty": uncertainty, "novelty": novelty,
    "hyperparameters": {"lookback": 14, "lstm_hidden": 64, "cnn_embedding": 32, "dropout": 0.3,
                        "lr": 1e-3, "batch_size": 128, "max_epochs": 25, "patience": 6},
}
(MODELS / "metrics.json").write_text(json.dumps(doc, indent=2), encoding="utf-8")
print("saved models/metrics.json")
