from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import exp
from pathlib import Path
from typing import Protocol

from app.ml.novelty import check_novelty

Features = Mapping[str, float | None]


@dataclass(frozen=True)
class Prediction:
    region_id: str
    risk_score: float
    disaster_type: str
    confidence: float
    novel: bool
    degraded: bool
    model_version: str
    top_features: list[tuple[str, float]]


class Predictor(Protocol):
    version: str

    def predict(self, region_id: str, features: Features, history: Sequence[Features]) -> Prediction: ...


class StatisticalBaselinePredictor:
    """Hand-weighted logistic fallback. Ignores `history`. Not evidence for the accuracy
    target; it's the safety net when the trained CNN-LSTM artefact is missing or fails to load."""

    version = "baseline-0.1"
    _BIAS = -3.5
    _W = {
        "rainfall_mm_24h": (100.0, 3.2),
        "river_level_m": (5.0, 2.6),
        "soil_moisture": (1.0, 1.2),
        "ndwi_mean": (1.0, 1.0),
    }

    def predict(self, region_id: str, features: Features, history: Sequence[Features]) -> Prediction:
        contribs: dict[str, float] = {}
        for name, (scale, weight) in self._W.items():
            v = features.get(name)
            if v is not None:
                contribs[name] = weight * v / scale
        z = self._BIAS + sum(contribs.values())
        score = 1.0 / (1.0 + exp(-z))

        degraded = features.get("ndwi_mean") is None
        missing_ground = sum(features.get(k) is None for k in ("river_level_m", "soil_moisture"))
        confidence = 0.85 - (0.15 if degraded else 0.0) - 0.05 * missing_ground
        novel, _ = check_novelty(dict(features))
        if novel:
            confidence *= 0.5
        top = sorted(contribs.items(), key=lambda kv: abs(kv[1]), reverse=True)
        return Prediction(
            region_id=region_id, risk_score=round(score, 4),
            disaster_type="unrecognised" if novel else "flood",
            confidence=round(max(confidence, 0.3) if not novel else confidence, 3),
            novel=novel, degraded=degraded, model_version=self.version,
            top_features=[(k, round(v, 3)) for k, v in top],
        )


class CnnLstmPredictor:
    """Loads the artefacts trained in notebooks/04_data_mining.ipynb. Requires a full lookback
    window of history; with fewer readings than that it reports degraded=True and lets the
    caller fall back to the baseline (see ModelRegistry.active_for). No satellite tile ingestion
    pipeline exists yet in this prototype, so the tile input is a neutral zero-array and every
    prediction from this model is marked degraded until real imagery is wired in."""

    LOOKBACK = 10
    SEQ_FEATURES = [
        "rainfall_mm_24h", "river_level_m", "soil_moisture", "temperature_c", "humidity_pct",
        "api_index",
    ]
    MISSING_FLAGS = [f"{c}_missing" for c in
                     ["rainfall_mm_24h", "river_level_m", "soil_moisture", "temperature_c", "humidity_pct"]]

    def __init__(self, models_dir: Path) -> None:
        import numpy as np  # pyright: ignore[reportMissingImports] — optional dependency
        try:
            import tensorflow as tf  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError("TensorFlow is required to load the CNN-LSTM predictor") from exc

        self._np = np
        meta = __import__("json").loads((models_dir / "artefact_meta.json").read_text())
        self.version = f"cnn-lstm-{meta['dataset_version']}"
        self._model = tf.keras.models.load_model(models_dir / "cnn_lstm.keras")
        self._autoencoder = tf.keras.models.load_model(models_dir / "novelty_ae.keras")
        self._novelty_threshold = float(meta["novelty_threshold"])
        d = np.load(models_dir / "model_ready.npz") if (models_dir / "model_ready.npz").exists() else None
        # fall back to zero-mean/unit-std if the normalisation stats weren't shipped
        self._seq_mean = d["seq_mean"] if d is not None else 0.0
        self._seq_std = d["seq_std"] if d is not None else 1.0
        self._tile_shape = tuple(self._model.input_shape[1][1:])

    def _row(self, f: Features) -> list[float]:
        api = f.get("rainfall_mm_24h") or 0.0  # a real deployment keeps a running API server-side;
        row = [f.get(c) or 0.0 for c in self.SEQ_FEATURES[:-1]] + [api]
        row += [1.0 if f.get(c) is None else 0.0 for c in self.MISSING_FLAGS]
        row += [0.0, 0.0, 0.0, 0.0]  # land-cover slot: unavailable without a region lookup here
        return row

    def predict(self, region_id: str, features: Features, history: Sequence[Features]) -> Prediction:
        np = self._np
        window = list(history[-self.LOOKBACK:]) + [features]
        if len(window) < self.LOOKBACK:
            raise ValueError("insufficient history for CNN-LSTM; caller should use the baseline")
        seq = np.array([self._row(f) for f in window[-self.LOOKBACK:]], dtype="float32")
        seq_norm = ((seq - self._seq_mean) / self._seq_std)[None, ...]
        tile = np.zeros((1,) + self._tile_shape, dtype="float32")  # no imagery pipeline yet

        score = float(self._model.predict({"sequence": seq_norm, "tile": tile}, verbose=0).ravel()[0])
        flat = seq_norm.reshape(1, -1)
        recon_err = float(np.mean((self._autoencoder.predict(flat, verbose=0) - flat) ** 2))
        novel = recon_err > self._novelty_threshold

        rule_novel, _ = check_novelty(dict(features))
        novel = novel or rule_novel
        confidence = 0.55 if novel else 0.9  # degraded because tile input is a placeholder
        return Prediction(
            region_id=region_id, risk_score=round(score, 4),
            disaster_type="unrecognised" if novel else "flood",
            confidence=confidence, novel=novel, degraded=True, model_version=self.version,
            top_features=[("rainfall_mm_24h", round(seq[-1, 0], 3)),
                          ("river_level_m", round(seq[-1, 1], 3))],
        )


class ModelRegistry:
    """Pluggable registry. `active_for` tries the trained model first and falls back cleanly if
    it errors or lacks enough history — this is the model-service decoupling the API depends on."""

    def __init__(self, fallback: Predictor) -> None:
        self._models: dict[str, Predictor] = {}
        self._fallback = fallback
        self._active: str | None = None

    def register(self, name: str, model: Predictor, activate: bool = False) -> None:
        self._models[name] = model
        if activate:
            self._active = name

    def active(self) -> Predictor:
        return self._models.get(self._active or "", self._fallback)

    def predict_with_fallback(
        self, region_id: str, features: Features, history: Sequence[Features]
    ) -> Prediction:
        primary = self._models.get(self._active or "")
        if primary is not None:
            try:
                return primary.predict(region_id, features, history)
            except Exception:
                pass  # graceful degradation: fall through to the baseline below
        return self._fallback.predict(region_id, features, history)


def load_registry() -> ModelRegistry:
    import logging

    log = logging.getLogger(__name__)
    registry = ModelRegistry(fallback=StatisticalBaselinePredictor())
    models_dir = Path(__file__).resolve().parents[3] / "models"
    try:
        if (models_dir / "cnn_lstm.keras").exists():
            registry.register("cnn_lstm", CnnLstmPredictor(models_dir), activate=True)
            log.info("cnn_lstm model loaded", extra={"ctx": {"models_dir": str(models_dir)}})
        else:
            log.warning("no trained model found; run the notebooks. Using statistical baseline.")
    except Exception:
        log.exception("failed to load cnn_lstm model; using statistical baseline")
    return registry