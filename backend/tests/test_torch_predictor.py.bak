import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

torch = pytest.importorskip("torch")
np = pytest.importorskip("numpy")

from app.ml.integrity import ModelIntegrityError, write_manifest  # noqa: E402
from app.ml.torch_predictor import CnnLstm, TorchPredictor  # noqa: E402

FEATS = [
    "rainfall_mm", "river_level_m", "temperature_c", "humidity_pct", "pressure_hpa", "wind_ms",
    "soil_moisture", "api", "river_level_m_missing", "soil_moisture_missing",
    "susceptibility_idx", "impervious_frac",
]


def _artifacts(d: Path) -> None:
    torch.manual_seed(0)
    torch.save(CnnLstm(n_feat=len(FEATS)).state_dict(), d / "ewsa_cnn_lstm.pt")
    prep = {
        "lookback": 14, "features": FEATS,
        "seq_mean": [10, 1, 20, 70, 1010, 5, 0.5, 50, 0, 0, 0.5, 0.3],
        "seq_std": [15, 1, 4, 10, 5, 2, 0.2, 60, 1, 1, 0.2, 0.2],
        "tile_mean": [0, 0, 0, 0], "tile_std": [1, 1, 1, 1], "api_decay": 0.85,
        "region_statics": {"KZN-ETHEKWINI": [0.85, 0.55]},
    }
    (d / "preprocessing.json").write_text(json.dumps(prep), encoding="utf-8")
    metrics = {"data_kind": "synthetic", "primary": "cnn_lstm",
               "models": {"cnn_lstm": {"threshold": 0.3}}}
    (d / "metrics.json").write_text(json.dumps(metrics), encoding="utf-8")


def _history(now: datetime, days: int = 14, skip: tuple[int, ...] = ()) -> list[dict[str, Any]]:
    return [
        {"observed_at": (now - timedelta(days=k)).isoformat(), "rainfall_mm_24h": 20.0 + k,
         "river_level_m": 1.0, "soil_moisture": 0.5, "temperature_c": 20.0, "humidity_pct": 70.0}
        for k in range(days) if k not in skip
    ]


def _load(tmp_path: Path, allow_synthetic: bool = True) -> TorchPredictor:
    return TorchPredictor.from_dir(tmp_path, tmp_path / "tiles", 0.6, False, allow_synthetic)


def test_predict_sequence_basic_and_degraded_flags(tmp_path: Path) -> None:
    _artifacts(tmp_path)
    p = _load(tmp_path)
    now = datetime.now(timezone.utc)
    pred = p.predict_sequence("KZN-ETHEKWINI", _history(now), now)
    assert pred is not None and 0.0 <= pred.risk_score <= 1.0
    assert pred.degraded is True and pred.model_version.startswith("cnn-lstm-")
    assert len(pred.top_features) <= 5

    (tmp_path / "tiles").mkdir()
    np.save(tmp_path / "tiles" / "KZN-ETHEKWINI.npy", np.zeros((4, 16, 16), dtype=np.float32))
    with_tile = p.predict_sequence("KZN-ETHEKWINI", _history(now), now)
    assert with_tile is not None and with_tile.degraded is False
    down = p.predict_sequence("KZN-ETHEKWINI", _history(now), now, satellite_up=False)
    assert down is not None and down.degraded is True


def test_history_requirements(tmp_path: Path) -> None:
    _artifacts(tmp_path)
    p = _load(tmp_path)
    now = datetime.now(timezone.utc)
    assert p.predict_sequence("KZN-ETHEKWINI", _history(now, days=3), now) is None
    assert p.predict_sequence("KZN-ETHEKWINI", _history(now, skip=(3,)), now) is not None
    assert p.predict_sequence("KZN-ETHEKWINI", _history(now, skip=(2, 3, 4)), now) is None


def test_refuses_synthetic_model_when_not_allowed(tmp_path: Path) -> None:
    _artifacts(tmp_path)
    with pytest.raises(ModelIntegrityError):
        _load(tmp_path, allow_synthetic=False)


def test_tampered_artefact_rejected(tmp_path: Path) -> None:
    _artifacts(tmp_path)
    write_manifest(tmp_path, ["ewsa_cnn_lstm.pt", "preprocessing.json", "metrics.json"])
    _load(tmp_path)  # verifies fine
    (tmp_path / "preprocessing.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ModelIntegrityError):
        _load(tmp_path)
