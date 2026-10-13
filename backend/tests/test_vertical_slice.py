import time
from typing import Any

from fastapi.testclient import TestClient

from tests.conftest import PASSWORD, auth, flood_payload, wait_for_alerts


def test_unauthenticated_requests_rejected(client: TestClient) -> None:
    assert client.post("/ingest/weather", json=flood_payload()).status_code in (401, 403)
    assert client.get("/alerts").status_code in (401, 403)


def test_bad_login_and_viewer_cannot_ingest(client: TestClient) -> None:
    r = client.post("/auth/login", json={"username": "admin", "password": "wrong"})
    assert r.status_code == 401
    viewer = auth(client, "viewer")
    assert client.post("/ingest/weather", json=flood_payload(), headers=viewer).status_code == 403
    assert client.get("/alerts", headers=viewer).status_code == 200


def test_ingest_produces_alert_under_60_seconds(client: TestClient) -> None:
    h = auth(client, "analyst")
    t0 = time.monotonic()
    assert client.post("/ingest/weather", json=flood_payload(), headers=h).status_code == 202
    alerts = wait_for_alerts(client, h)
    elapsed = time.monotonic() - t0
    assert alerts, "no alert produced"
    a = alerts[0]
    assert elapsed < 60 and a["latency_ms"] < 60_000
    assert a["severity"] == "critical" and a["disaster_type"] == "flood"
    assert a["degraded"] is True  # no satellite data supplied -> reduced-confidence mode
    assert a["explanation"][0]["feature"] == "rainfall_mm_24h"


def test_ingestion_is_idempotent(client: TestClient) -> None:
    h = auth(client, "analyst")
    payload = flood_payload()
    first = client.post("/ingest/weather", json=payload, headers=h).json()
    wait_for_alerts(client, h)
    second = client.post("/ingest/weather", json=payload, headers=h).json()
    time.sleep(0.5)
    assert first["status"] == "accepted" and second["status"] == "duplicate"
    assert len(client.get("/alerts", headers=h).json()) == 1


def test_invalid_input_rejected(client: TestClient) -> None:
    h = auth(client, "analyst")
    bad = flood_payload() | {"lat": 51.5}  # London, outside South Africa
    assert client.post("/ingest/weather", json=bad, headers=h).status_code == 422
    bad = flood_payload() | {"rainfall_mm_24h": -5}
    assert client.post("/ingest/weather", json=bad, headers=h).status_code == 422


def test_benign_reading_raises_no_alert(client: TestClient) -> None:
    h = auth(client, "analyst")
    calm = flood_payload("SAWS-CALM1") | {
        "rainfall_mm_24h": 2, "river_level_m": 0.8, "soil_moisture": 0.3}
    client.post("/ingest/weather", json=calm, headers=h)
    time.sleep(1.0)
    assert client.get("/alerts", headers=h).json() == []


def test_novel_input_flagged_not_misclassified(client: TestClient) -> None:
    h = auth(client, "analyst")
    extreme = flood_payload("SAWS-XTRM1") | {"rainfall_mm_24h": 700}  # beyond training envelope
    client.post("/ingest/weather", json=extreme, headers=h)
    a = wait_for_alerts(client, h)[0]
    assert a["novel"] is True and a["disaster_type"] == "unrecognised"


def test_alert_workflow_and_websocket(client: TestClient) -> None:
    h = auth(client, "analyst")
    token = h["Authorization"].split()[1]
    with client.websocket_connect("/ws/alerts") as ws:
        ws.send_json({"token": token})
        time.sleep(0.3)  # let the server register the socket before ingesting
        client.post("/ingest/weather", json=flood_payload(), headers=h)
        pushed: dict[str, Any] = ws.receive_json()
    assert pushed["severity"] == "critical"
    aid = pushed["id"]
    assert client.post(f"/alerts/{aid}/ack", headers=h).json()["status"] == "acknowledged"
    assert client.post(f"/alerts/{aid}/ack", headers=h).status_code == 409
    assert client.post(f"/alerts/{aid}/resolve", headers=h).json()["status"] == "resolved"


def test_websocket_rejects_bad_token(client: TestClient) -> None:
    with client.websocket_connect("/ws/alerts") as ws:
        ws.send_json({"token": "not-a-jwt"})
        try:
            ws.receive_json()
            raise AssertionError("expected close")
        except Exception as exc:  # starlette raises WebSocketDisconnect on close
            assert "AssertionError" not in type(exc).__name__


def test_health_endpoints(client: TestClient) -> None:
    assert client.get("/health/live").json() == {"status": "ok"}
    body = client.get("/health/ready").json()
    assert body["checks"]["database"] == "ok" and PASSWORD  # PASSWORD import keeps linters quiet