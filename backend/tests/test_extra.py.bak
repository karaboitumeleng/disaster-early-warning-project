import asyncio
import time
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.resilience import CircuitBreaker, CircuitOpenError, call_with_resilience
from tests.conftest import auth, flood_payload, wait_for_alerts


def test_circuit_breaker_opens_and_recovers() -> None:
    now = [0.0]
    cb = CircuitBreaker(failure_threshold=2, reset_after_s=10, clock=lambda: now[0])
    cb.record_failure()
    assert cb.state == "closed"
    cb.record_failure()
    assert cb.state == "open" and not cb.allow()
    now[0] = 11.0
    assert cb.state == "half_open" and cb.allow()
    cb.record_success()
    assert cb.state == "closed"


def test_retry_then_success() -> None:
    calls = {"n": 0}

    async def flaky() -> str:
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("boom")
        return "ok"

    cb = CircuitBreaker(failure_threshold=10)
    assert asyncio.run(call_with_resilience(flaky, cb, retries=3, base_delay=0.001)) == "ok"
    assert calls["n"] == 3


def test_open_circuit_short_circuits() -> None:
    cb = CircuitBreaker(failure_threshold=1, reset_after_s=1000)

    async def bad() -> str:
        raise RuntimeError("x")

    with pytest.raises(RuntimeError):
        asyncio.run(call_with_resilience(bad, cb, retries=0, base_delay=0.001))
    with pytest.raises(CircuitOpenError):
        asyncio.run(call_with_resilience(bad, cb, retries=0, base_delay=0.001))


def _wait_n(client: TestClient, headers: dict[str, str], n: int, timeout: float = 10) -> list[Any]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        alerts = client.get("/alerts", headers=headers).json()
        if len(alerts) >= n:
            return list(alerts)
        time.sleep(0.1)
    return []


def test_satellite_outage_forces_degraded_mode(client: TestClient) -> None:
    analyst, admin = auth(client, "analyst"), auth(client, "admin")
    p1 = flood_payload("SAWS-A1") | {"ndwi_mean": 0.6}
    client.post("/ingest/weather", json=p1, headers=analyst)
    first = wait_for_alerts(client, analyst)
    assert first and first[0]["degraded"] is False  # satellite data used

    assert client.post("/feeds/satellite/down", headers=analyst).status_code == 403
    assert client.post("/feeds/satellite/down", headers=admin).status_code == 200
    assert any(f["name"] == "satellite" and f["state"] == "down"
               for f in client.get("/feeds", headers=analyst).json())
    assert client.get("/health/ready").status_code in (200, 401, 403)

    p2 = flood_payload("SAWS-A2") | {"ndwi_mean": 0.6}
    client.post("/ingest/weather", json=p2, headers=analyst)
    alerts = _wait_n(client, analyst, 2)
    assert len(alerts) == 2 and alerts[0]["degraded"] is True  # newest alert, degraded


def test_regions_risk_and_timeseries(client: TestClient) -> None:
    analyst, viewer = auth(client, "analyst"), auth(client, "viewer")
    client.post("/ingest/weather", json=flood_payload(), headers=analyst)
    wait_for_alerts(client, analyst)
    regions = client.get("/regions/risk", headers=viewer).json()
    eth = next(r for r in regions if r["id"] == "KZN-ETHEKWINI")
    assert eth["level"] == "critical" and eth["risk"] > 0.9
    assert any(r["risk"] is None for r in regions)
    ts = client.get("/regions/KZN-ETHEKWINI/timeseries", headers=viewer).json()
    assert len(ts) == 1 and ts[0]["risk"] > 0.9
    assert client.get("/regions/risk").status_code in (401, 403)


def test_model_metrics_absent_is_reported(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MODELS_DIR", str(tmp_path))
    body = client.get("/model/metrics", headers=auth(client, "viewer")).json()
    assert body["available"] is False and body["active_model"].startswith("baseline")
