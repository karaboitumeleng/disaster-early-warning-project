import time

from fastapi.testclient import TestClient

from tests.conftest import auth, flood_payload, wait_for_alerts


def test_readings_endpoint(client: TestClient) -> None:
    h = auth(client, "analyst")
    client.post("/ingest/weather", json=flood_payload("SAWS-TS1"), headers=h)
    wait_for_alerts(client, h)
    rows = client.get("/regions/KZN-ETHEKWINI/readings", headers=h).json()
    assert rows and rows[-1]["rainfall_mm_24h"] == 180


def test_model_metrics_reports_unavailable_without_training(client: TestClient) -> None:
    h = auth(client, "viewer")
    body = client.get("/models/metrics", headers=h).json()
    assert body["available"] is False
    assert body["active_model_version"].startswith("baseline")