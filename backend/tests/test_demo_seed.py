from fastapi.testclient import TestClient

from tests.conftest import auth


def test_dashboard_is_populated_on_first_startup(client: TestClient) -> None:
    """No ingestion call made by the test — this checks the auto-seed alone."""
    viewer = auth(client, "viewer")

    regions = client.get("/regions", headers=viewer).json()
    bands = {r["id"]: r["band"] for r in regions}
    assert bands["KZN-ETHEKWINI"] == "high"
    assert bands["KZN-UMGUNGUNDLOVU"] == "low"  # proves it's not uniformly red

    alerts = client.get("/alerts", headers=viewer).json()
    assert len(alerts) >= 5
    assert any(a["region_id"] == "KZN-ETHEKWINI" and a["severity"] == "critical" for a in alerts)
    assert any(a["novel"] and a["region_id"] == "MP-NKANGALA" for a in alerts)

    readings = client.get("/regions/KZN-ETHEKWINI/readings", headers=viewer).json()
    assert len(readings) == 7  # full escalation history for the time-series chart