import time

from fastapi.testclient import TestClient

from tests.conftest import auth, flood_payload, wait_for_alerts


def test_first_ever_reading_for_a_region_still_predicts(client: TestClient) -> None:
    """No trained model is present in CI, so this always exercises the baseline path with
    zero history — the real regression this guards is the CNN-LSTM path raising on short
    history and the registry NOT catching it."""
    h = auth(client, "analyst")
    r = client.post("/ingest/weather", json=flood_payload("SAWS-FIRST1"), headers=h)
    assert r.status_code == 202
    alerts = wait_for_alerts(client, h)
    assert alerts and alerts[0]["model_version"].startswith("baseline")