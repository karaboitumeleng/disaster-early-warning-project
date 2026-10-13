import json
from pathlib import Path

from app.schemas import ModelMetrics


def load_model_metrics(models_dir: Path, active_version: str) -> ModelMetrics:
    path = models_dir / "metrics.json"
    if not path.exists():
        return ModelMetrics(available=False, active_model_version=active_version,
                             note="No trained model yet — run notebooks 01-05, then restart the API.")
    data = json.loads(path.read_text())
    return ModelMetrics(available=True, active_model_version=active_version, **data)