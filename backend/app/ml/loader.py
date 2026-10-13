"""Builds the model registry: CNN-LSTM if artefacts + torch are available and verified,
otherwise the statistical baseline. Never raises: the API must start regardless."""
import logging
from pathlib import Path

from app.config import Settings
from app.ml.predictor import ModelRegistry, load_registry

log = logging.getLogger(__name__)


def build_registry(settings: Settings) -> ModelRegistry:
    registry = load_registry()
    if not settings.use_torch_model:
        log.info("CNN-LSTM disabled by USE_TORCH_MODEL; using baseline")
        return registry
    models_dir = Path(settings.models_dir)
    if not (models_dir / "ewsa_cnn_lstm.pt").is_file():
        log.info("no CNN-LSTM artefact in %s; using baseline", models_dir)
        return registry
    try:
        from app.ml.torch_predictor import TorchPredictor

        dev = settings.app_env == "dev"
        model = TorchPredictor.from_dir(
            models_dir,
            Path(settings.tiles_dir),
            settings.alert_threshold,
            require_manifest=not dev,
            allow_synthetic=dev,
        )
    except ImportError:
        log.warning("torch/numpy not installed; using baseline (pip install -r requirements-ml.txt)")
    except Exception:
        log.exception("CNN-LSTM failed to load or verify; using baseline")
    else:
        registry.register("cnn_lstm", model, activate=True)
        log.info("CNN-LSTM active", extra={"ctx": {"model": model.version}})
    return registry
