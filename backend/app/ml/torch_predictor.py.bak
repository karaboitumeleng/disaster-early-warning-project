"""CNN-LSTM predictor for the live alert path (imported lazily; needs numpy + torch).

Input assembly mirrors notebooks 03/04 exactly:
  * daily series per region = LAST reading of each UTC day (multi-station data is not averaged)
  * 14-day lookback window, features in the order stored in models/preprocessing.json
  * antecedent-precipitation index recomputed over up to 45 days of history (decay from prefs)
  * absent days: rainfall = 0, other variables carried forward, missing-flags = 1
    (at most `max_filled_days` absent days in the window, else the caller falls back to baseline)
  * satellite tile from data/tiles/<REGION>.npy; missing tile or satellite feed down => blank
    (mean) tile + degraded flag. Notebook 04 trains with tile dropout so this is in-distribution.
Keep CnnLstm identical to the class in notebooks/src/04_data_mining.py."""
from __future__ import annotations

import json
import logging
import math
import re
import threading
from collections.abc import Mapping, Sequence
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch import nn

from app.ml.integrity import (
    OPTIONAL,
    REQUIRED,
    ModelIntegrityError,
    sha256_file,
    verify_manifest,
)
from app.ml.novelty import check_novelty
from app.ml.predictor import Prediction, StatisticalBaselinePredictor
from app.ml.scoring import rescale

log = logging.getLogger(__name__)

TILE = 16
_ID = re.compile(r"^[A-Za-z0-9_-]+$")
_KEYMAP = {  # training feature -> live payload key
    "rainfall_mm": "rainfall_mm_24h",
    "river_level_m": "river_level_m",
    "temperature_c": "temperature_c",
    "humidity_pct": "humidity_pct",
    "pressure_hpa": "pressure_hpa",
    "wind_ms": "wind_ms",
    "soil_moisture": "soil_moisture",
}
_VARS = list(_KEYMAP)
_KNOWN = set(_KEYMAP) | {
    "api",
    "river_level_m_missing",
    "soil_moisture_missing",
    "susceptibility_idx",
    "impervious_frac",
}
_ENVELOPE_KEYS = (
    "rainfall_mm_24h",
    "river_level_m",
    "soil_moisture",
    "temperature_c",
    "humidity_pct",
)
AE_MARGIN = 1.5  # flag as novel only above 1.5x the autoencoder's 99th-percentile train error
TOP_K = 5
MC_SAMPLES = 20


class CnnLstm(nn.Module):
    def __init__(self, n_feat: int, hidden: int = 64, emb: int = 32, p: float = 0.3) -> None:
        super().__init__()
        self.cnn = nn.Sequential(
            nn.Conv2d(4, 16, 3, padding=1),
            nn.BatchNorm2d(16),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(16, 32, 3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
            nn.Linear(32, emb),
            nn.ReLU(),
        )
        self.lstm = nn.LSTM(n_feat, hidden, batch_first=True)
        self.head = nn.Sequential(
            nn.Dropout(p), nn.Linear(hidden + emb, 32), nn.ReLU(), nn.Dropout(p), nn.Linear(32, 1)
        )

    def forward(self, seq: torch.Tensor, tile: torch.Tensor) -> torch.Tensor:
        _, (h, _) = self.lstm(seq)
        return self.head(torch.cat([h[-1], self.cnn(tile)], dim=1)).squeeze(1)


def _autoencoder(d: int) -> nn.Sequential:
    return nn.Sequential(
        nn.Linear(d, 16),
        nn.ReLU(),
        nn.Linear(16, 6),
        nn.ReLU(),
        nn.Linear(6, 16),
        nn.ReLU(),
        nn.Linear(16, d),
    )


def _parse_ts(v: Any) -> datetime | None:
    if isinstance(v, datetime):
        dt = v
    elif isinstance(v, str):
        try:
            dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    return (dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)


def _daily_last(
    history: Sequence[Mapping[str, Any]], as_of: datetime
) -> dict[date, Mapping[str, Any]]:
    best: dict[date, tuple[datetime, Mapping[str, Any]]] = {}
    for p in history:
        ts = _parse_ts(p.get("observed_at"))
        if ts is None or ts > as_of:
            continue
        cur = best.get(ts.date())
        if cur is None or ts >= cur[0]:
            best[ts.date()] = (ts, p)
    return {d: v[1] for d, v in best.items()}


def _fill(col: np.ndarray, default: float) -> np.ndarray:
    """Forward-fill, then back-fill leading gaps, else `default`."""
    valid = np.flatnonzero(~np.isnan(col))
    if valid.size == 0:
        return np.full_like(col, default)
    idx = np.where(~np.isnan(col), np.arange(len(col)), 0)
    np.maximum.accumulate(idx, out=idx)
    out = col[idx]
    out[: valid[0]] = col[valid[0]]
    return out


class TorchPredictor:
    max_filled_days = 2

    def __init__(
        self,
        model: nn.Module,
        prep: Mapping[str, Any],
        threshold: float,
        alert_threshold: float,
        tiles_dir: Path,
        version: str,
        ae: nn.Module | None = None,
        ae_threshold: float | None = None,
    ) -> None:
        self.model = model.eval()
        self.feats: list[str] = list(prep["features"])
        unknown = [f for f in self.feats if f not in _KNOWN]
        if unknown or "rainfall_mm" not in self.feats:
            raise ValueError(f"unsupported feature set: {self.feats}")
        self.lookback_days = int(prep["lookback"])
        self.history_days = max(45, self.lookback_days)
        self.mean = np.asarray(prep["seq_mean"], dtype=np.float32)
        self.std = np.asarray(prep["seq_std"], dtype=np.float32)
        if len(self.mean) != len(self.feats) or len(self.std) != len(self.feats):
            raise ValueError("preprocessing stats do not match feature list")
        self.tile_mean = np.asarray(prep["tile_mean"], dtype=np.float32).reshape(4, 1, 1)
        self.tile_std = np.asarray(prep["tile_std"], dtype=np.float32).reshape(4, 1, 1)
        self.decay = float(prep.get("api_decay", 0.85))
        self.statics: Mapping[str, Sequence[float]] = prep.get("region_statics", {})
        self.threshold = threshold
        self.alert_threshold = alert_threshold
        self.tiles_dir = tiles_dir
        self.version = version
        self.ae = ae.eval() if ae is not None else None
        self.ae_threshold = ae_threshold
        self._rain_i = self.feats.index("rainfall_mm")
        self._baseline = StatisticalBaselinePredictor()
        self._lock = threading.Lock()  # model mode toggling (MC dropout) is not thread-safe
        self._tile_cache: dict[str, tuple[float, np.ndarray]] = {}

    # ---- loading -------------------------------------------------------
    @classmethod
    def from_dir(
        cls,
        models_dir: Path,
        tiles_dir: Path,
        alert_threshold: float,
        require_manifest: bool,
        allow_synthetic: bool,
    ) -> TorchPredictor:
        names = [n for n in (*REQUIRED, *OPTIONAL) if (models_dir / n).is_file()]
        verify_manifest(models_dir, names, require_manifest)
        prep = json.loads((models_dir / "preprocessing.json").read_text(encoding="utf-8"))
        metrics = json.loads((models_dir / "metrics.json").read_text(encoding="utf-8"))
        kind = str(metrics.get("data_kind", "unknown"))
        if kind != "real" and not allow_synthetic:
            raise ModelIntegrityError(f"model trained on {kind} data; refusing outside dev")
        hp = metrics.get("hyperparameters", {})
        model = CnnLstm(
            n_feat=len(prep["features"]),
            hidden=int(hp.get("lstm_hidden", 64)),
            emb=int(hp.get("cnn_embedding", 32)),
            p=float(hp.get("dropout", 0.3)),
        )
        state = torch.load(models_dir / "ewsa_cnn_lstm.pt", map_location="cpu", weights_only=True)
        model.load_state_dict(state)
        ae: nn.Module | None = None
        ae_thr: float | None = None
        if (models_dir / "autoencoder.pt").is_file() and "novelty" in metrics:
            ae = _autoencoder(len(prep["features"]) + 2)
            ae.load_state_dict(
                torch.load(models_dir / "autoencoder.pt", map_location="cpu", weights_only=True)
            )
            ae_thr = float(metrics["novelty"]["threshold"]) * AE_MARGIN
        thr = float(metrics["models"][metrics["primary"]]["threshold"])
        version = f"cnn-lstm-{sha256_file(models_dir / 'ewsa_cnn_lstm.pt')[:8]}-{kind}"[:32]
        return cls(model, prep, thr, alert_threshold, tiles_dir, version, ae, ae_thr)

    # ---- Predictor protocol (single reading, no history) ------------------
    def predict(self, region_id: str, features: Mapping[str, float | None]) -> Prediction:
        """No window available here: delegate to the statistical baseline (used by the
        analytics overlay). The alert path calls predict_sequence instead."""
        return self._baseline.predict(region_id, features)

    # ---- sequence path -----------------------------------------------------
    def _tile(self, region_id: str, satellite_up: bool) -> np.ndarray | None:
        if not satellite_up or not _ID.fullmatch(region_id):
            return None
        path = self.tiles_dir / f"{region_id}.npy"
        try:
            mtime = path.stat().st_mtime
        except OSError:
            return None
        cached = self._tile_cache.get(region_id)
        if cached and cached[0] == mtime:
            return cached[1]
        try:
            arr = np.load(path, allow_pickle=False).astype(np.float32)
        except (OSError, ValueError):
            log.warning("unreadable tile for %s", region_id)
            return None
        if arr.shape != (4, TILE, TILE) or not np.isfinite(arr).all():
            log.warning("bad tile shape/values for %s", region_id)
            return None
        norm = ((arr - self.tile_mean) / self.tile_std).astype(np.float32)
        self._tile_cache[region_id] = (mtime, norm)
        return norm

    def _window(
        self, region_id: str, history: Sequence[Mapping[str, Any]], as_of: datetime
    ) -> tuple[np.ndarray, int, Mapping[str, Any]] | None:
        as_of = as_of if as_of.tzinfo else as_of.replace(tzinfo=timezone.utc)
        as_of = as_of.astimezone(timezone.utc)
        days = _daily_last(history, as_of)
        end = as_of.date()
        span = self.history_days
        grid = [end - timedelta(days=span - 1 - i) for i in range(span)]
        present = np.array([d in days for d in grid])
        filled = int((~present[-self.lookback_days :]).sum())
        if not present[-1] or filled > self.max_filled_days:
            return None
        raw = np.full((span, len(_VARS)), np.nan, dtype=np.float64)
        for i, d in enumerate(grid):
            p = days.get(d)
            if p is None:
                continue
            for j, name in enumerate(_VARS):
                v = p.get(_KEYMAP[name])
                if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v):
                    raw[i, j] = float(v)

        def default_for(name: str) -> float:
            return float(self.mean[self.feats.index(name)]) if name in self.feats else 0.0

        cols: dict[str, np.ndarray] = {}
        for j, name in enumerate(_VARS):
            if name == "rainfall_mm":
                cols[name] = np.nan_to_num(raw[:, j], nan=0.0)
            else:
                cols[name] = _fill(raw[:, j], default_for(name))
        cols["river_level_m_missing"] = np.isnan(raw[:, _VARS.index("river_level_m")]).astype(float)
        cols["soil_moisture_missing"] = np.isnan(raw[:, _VARS.index("soil_moisture")]).astype(float)
        rain = cols["rainfall_mm"]
        api = np.empty(span)
        api[0] = rain[0]
        for t in range(1, span):
            api[t] = self.decay * api[t - 1] + rain[t]
        cols["api"] = api
        stat = self.statics.get(region_id)
        for k, name in enumerate(("susceptibility_idx", "impervious_frac")):
            value = float(stat[k]) if stat is not None else default_for(name)
            cols[name] = np.full(span, value)
        x = np.stack([cols[f][-self.lookback_days :] for f in self.feats], axis=1)
        return x.astype(np.float32), filled, days[end]

    def _infer(
        self, xs: np.ndarray, tile: np.ndarray, tile_used: bool, tab: np.ndarray
    ) -> tuple[float, dict[str, float], float, float | None]:
        n_feat = xs.shape[1]
        seq_b = np.repeat(xs[None], n_feat + 2, axis=0)  # row 0 = as-is, then one row per occlusion
        for j in range(n_feat):
            seq_b[j + 1, :, j] = 0.0  # replace feature by its training mean
        tile_b = np.repeat(tile[None], n_feat + 2, axis=0)
        tile_b[n_feat + 1] = 0.0
        with self._lock, torch.no_grad():
            self.model.eval()
            out = self.model(torch.from_numpy(seq_b), torch.from_numpy(tile_b)).numpy()
            base = float(out[0])
            deltas = {self.feats[j]: base - float(out[j + 1]) for j in range(n_feat)}
            if tile_used:
                deltas["satellite_tile"] = base - float(out[n_feat + 1])
            for m in self.model.modules():
                if isinstance(m, nn.Dropout):
                    m.train()
            try:
                p = torch.sigmoid(
                    self.model(
                        torch.from_numpy(np.repeat(xs[None], MC_SAMPLES, axis=0)),
                        torch.from_numpy(np.repeat(tile[None], MC_SAMPLES, axis=0)),
                    )
                ).numpy()
            finally:
                self.model.eval()
            ae_err: float | None = None
            if self.ae is not None:
                x = torch.from_numpy(tab[None])
                ae_err = float(((self.ae(x) - x) ** 2).mean().item())
        return base, deltas, float(p.std()), ae_err

    def predict_sequence(
        self,
        region_id: str,
        history: Sequence[Mapping[str, Any]],
        as_of: datetime,
        satellite_up: bool = True,
    ) -> Prediction | None:
        """Returns None when there is not enough history; the caller then uses the baseline."""
        built = self._window(region_id, history, as_of)
        if built is None:
            return None
        x, filled, latest = built
        xs = ((x - self.mean) / self.std).astype(np.float32)
        tile = self._tile(region_id, satellite_up)
        tile_used = tile is not None
        tile_in = tile if tile is not None else np.zeros((4, TILE, TILE), dtype=np.float32)
        tab = np.concatenate(
            [xs[-1], [xs[-3:, self._rain_i].sum(), xs[-7:, self._rain_i].sum()]]
        ).astype(np.float32)
        logit, deltas, mc_std, ae_err = self._infer(xs, tile_in, tile_used, tab)

        p = 1.0 / (1.0 + math.exp(-max(min(logit, 30.0), -30.0)))
        env_novel, _ = check_novelty({k: latest.get(k) for k in _ENVELOPE_KEYS})
        ae_novel = ae_err is not None and self.ae_threshold is not None and ae_err > self.ae_threshold
        novel = bool(env_novel or ae_novel)

        confidence = min(max(1.0 - 4.0 * mc_std, 0.3), 0.95) - 0.05 * filled
        if not tile_used:
            confidence -= 0.10
        if novel:
            confidence *= 0.5
        top = sorted(deltas.items(), key=lambda kv: abs(kv[1]), reverse=True)[:TOP_K]
        return Prediction(
            region_id=region_id,
            risk_score=round(rescale(p, self.threshold, self.alert_threshold), 4),
            disaster_type="unrecognised" if novel else "flood",
            confidence=round(max(confidence, 0.1), 3),
            novel=novel,
            degraded=not tile_used,
            model_version=self.version,
            top_features=[(k, round(v, 3)) for k, v in top],
        )
