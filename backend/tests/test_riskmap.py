from fastapi.testclient import TestClient

from tests.conftest import auth, flood_payload, wait_for_alerts


def test_regions_require_auth(client: TestClient) -> None:
    assert client.get("/regions").status_code in (401, 403)


def test_regions_seeded_and_band_updates_after_alert(client: TestClient) -> None:
    h = auth(client, "viewer")
    regions = client.get("/regions", headers=h).json()
    assert len(regions) == 5
    ethekwini = next(r for r in regions if r["id"] == "KZN-ETHEKWINI")
    assert ethekwini["band"] == "low" and ethekwini["last_updated"] is None

    writer = auth(client, "analyst")
    client.post("/ingest/weather", json=flood_payload(), headers=writer)
    wait_for_alerts(client, writer)

    updated = next(r for r in client.get("/regions", headers=h).json() if r["id"] == "KZN-ETHEKWINI")
    assert updated["band"] == "high" and updated["risk_score"] >= 0.7 and updated["last_updated"]