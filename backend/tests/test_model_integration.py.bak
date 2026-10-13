import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.ml.integrity import ModelIntegrityError, verify_manifest, write_manifest
from app.ml.predictor import Prediction, StatisticalBaselinePredictor
from app.ml.scoring import rescale
from tests.conftest import auth, flood_payload


def test_rescale_maps_threshold_and_is_monotone() -> None:
    assert rescale(0.3, 0.3, 0.6) == pytest.approx(0.6)
    assert rescale(0.0, 0.3, 0.6) == 0.0 and rescale(1.0, 0.3, 0.6) == pytest.approx(1.0)
    xs = [rescale(p / 100, 0.3, 0.6) for p in range(101)]
    assert xs == sorted(xs)


def test_manifest_roundtrip_and_tamper(tmp_path: Path) -> None:
    (tmp_path / "a.bin").write_bytes(b"one")
    write_manifest(tmp_path, ["a.bin"])
    verify_manifest(tmp_path, ["a.bin"], require_manifest=True)
    (tmp_path / "a.bin").write_bytes(b"two")
    with pytest.raises(ModelIntegrityError):
        verify_manifest(tmp_path, ["a.bin"], require_manifest=False)


def test_missing_manifest_policy(tmp_path: Path) -> None:
    (tmp_path / "a.bin").write_bytes(b"x")
    verify_manifest(tmp_path, ["a.bin"], require_manifest=False)
    with pytest.raises(ModelIntegrityError):
        verify_manifest(tmp_path, ["a.bin"], require_manifest=True)


class FakeSeq:
    """Stands in for a sequence model so the service wiring is tested without torch."""

    version = "fake-seq"
    history_days = 45

    def __init__(self, fail: bool = False, min_history: int = 3) -> None:
        self.fail, self.min_history = fail, min_history

    def predict(self, region_id: str, features: Any) -> Prediction:
        return StatisticalBaselinePredictor().predict(region_id, features)

    def predict_sequence(
        self, region_id: str, history: Any, as_of: datetime, satellite_up: bool = True
    ) -> Prediction | None:
        if self.fail:
            raise RuntimeError("boom")
        if len(history) < self.min_history:
            return None
        return Prediction(region_id, 0.95, "flood", 0.7, False, False, self.version,
                          [("rainfall_mm", 1.0)])


def _post(client: TestClient, headers: dict[str, str], station: str, ts: datetime) -> None:
    payload = flood_payload(station) | {"observed_at": ts.isoformat()}
    assert client.post("/ingest/weather", json=payload, headers=headers).status_code == 202


def _wait_n(client: TestClient, headers: dict[str, str], n: int, timeout: float = 10) -> list[Any]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        alerts = client.get("/alerts", headers=headers).json()
        if len(alerts) >= n:
            return list(alerts)
        time.sleep(0.1)
    return []


def test_sequence_model_used_only_with_enough_history(client: TestClient) -> None:
    client.app.state.registry.register("fake", FakeSeq(), activate=True)  # type: ignore[attr-defined]
    h = auth(client, "analyst")
    now = datetime.now(timezone.utc)
    for i, days in enumerate((2, 1, 0)):
        _post(client, h, f"SAWS-H{i}", now - timedelta(days=days, minutes=1))
    alerts = _wait_n(client, h, 3)
    versions = [a["model_version"] for a in alerts]
    assert len(alerts) == 3
    assert "fake-seq" in versions  # third reading saw 3 readings of history
    assert any(v.startswith("baseline") for v in versions)  # earlier ones fell back


def test_sequence_model_failure_falls_back_to_baseline(client: TestClient) -> None:
    client.app.state.registry.register("bad", FakeSeq(fail=True), activate=True)  # type: ignore[attr-defined]
    h = auth(client, "analyst")
    _post(client, h, "SAWS-F1", datetime.now(timezone.utc) - timedelta(minutes=1))
    alerts = _wait_n(client, h, 1)
    assert alerts and alerts[0]["model_version"].startswith("baseline")
    assert alerts[0]["disaster_type"] == "flood"
