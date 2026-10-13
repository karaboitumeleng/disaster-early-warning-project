"""Scripted flood scenario for a live presentation. Sends a sequence of realistic sensor
readings to the running API and narrates each one in the terminal, timed so the presenter
can talk over the pauses while the dashboard (projected/shared) updates live.

Run this AFTER the backend and frontend are already running (see docs/DEMO_SCRIPT.md).
Loosely mirrors the real April 2022 KZN event: calm -> rain arrives -> intensifies -> flood.
"""
import argparse
import sys
import time
from datetime import datetime, timedelta, timezone

import httpx

BANNER = r"""
=========================================================
  SA NATURAL DISASTER EARLY WARNING SYSTEM - LIVE DEMO
=========================================================
"""


def narrate(text: str, pause: float) -> None:
    print(f"\n>>> {text}")
    time.sleep(pause)


def send(client: httpx.Client, headers: dict, payload: dict) -> tuple[float, dict]:
    t0 = time.perf_counter()
    r = client.post("/ingest/weather", json=payload, headers=headers)
    r.raise_for_status()
    return t0, r.json()


def wait_for_new_alert(client: httpx.Client, headers: dict, seen_ids: set[int], timeout: float = 60):
    deadline = time.perf_counter() + timeout
    while time.perf_counter() < deadline:
        alerts = client.get("/alerts", headers=headers).json()
        new = [a for a in alerts if a["id"] not in seen_ids]
        if new:
            return new[0]
        time.sleep(0.2)
    return None


def iso(days_ago: int, hour: int = 6) -> str:
    dt = datetime.now(timezone.utc).replace(hour=hour, minute=0, second=0, microsecond=0) - timedelta(days=days_ago)
    return dt.isoformat()


def build_scenario() -> list[dict]:
    """Each step: narration text, pause before sending (s), and the payload."""
    return [
        {
            "text": "Day -3. Normal late-summer conditions in eThekwini (Durban). "
                     "Watch the Risk Map tab — this region should be sitting green, LOW risk.",
            "pause": 4,
            "payload": {
                "station_id": "SAWS-DBN-DEMO", "region_id": "KZN-ETHEKWINI",
                "observed_at": iso(3), "lat": -29.8579, "lon": 31.0292,
                "rainfall_mm_24h": 3, "river_level_m": 0.9, "soil_moisture": 0.32,
                "temperature_c": 22, "humidity_pct": 68,
            },
        },
        {
            "text": "Day -2. SAWS stations start reporting rain moving in off the coast. "
                     "Watch the risk band tick upward.",
            "pause": 4,
            "payload": {
                "station_id": "SAWS-DBN-DEMO", "region_id": "KZN-ETHEKWINI",
                "observed_at": iso(2), "lat": -29.8579, "lon": 31.0292,
                "rainfall_mm_24h": 28, "river_level_m": 1.4, "soil_moisture": 0.48,
                "temperature_c": 20, "humidity_pct": 82,
            },
        },
        {
            "text": "Day -1. Rainfall is intensifying and the ground is saturated from "
                     "yesterday. Expect this one to cross into WARNING.",
            "pause": 4,
            "payload": {
                "station_id": "SAWS-DBN-DEMO", "region_id": "KZN-ETHEKWINI",
                "observed_at": iso(1), "lat": -29.8579, "lon": 31.0292,
                "rainfall_mm_24h": 65, "river_level_m": 3.2, "soil_moisture": 0.71,
                "temperature_c": 19, "humidity_pct": 91,
            },
        },
        {
            "text": "Day 0. Torrential rain — this mirrors the real 11 April 2022 KZN event "
                     "(over 100mm in 24 hours). Watch for a CRITICAL alert to fire on the "
                     "Live Alerts tab within seconds, with the map marker pulsing red.",
            "pause": 5,
            "payload": {
                "station_id": "SAWS-DBN-DEMO", "region_id": "KZN-ETHEKWINI",
                "observed_at": iso(0), "lat": -29.8579, "lon": 31.0292,
                "rainfall_mm_24h": 182, "river_level_m": 6.8, "soil_moisture": 0.95,
                "temperature_c": 18, "humidity_pct": 97,
            },
        },
    ]


def build_novelty_step() -> dict:
    return {
        "text": "Now a different kind of moment: a sensor reports a reading far outside "
                 "anything the system has ever seen — this is the Open World ML hook. "
                 "Instead of confidently guessing, it should flag 'unrecognised pattern'.",
        "pause": 4,
        "payload": {
            "station_id": "SAWS-NKG-DEMO", "region_id": "MP-NKANGALA",
            "observed_at": iso(0, hour=9), "lat": -25.70, "lon": 29.35,
            "rainfall_mm_24h": 640, "river_level_m": 0.8, "soil_moisture": 0.4,
            "temperature_c": 21, "humidity_pct": 55,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api-url", default="http://localhost:8000")
    ap.add_argument("--user", default="analyst")
    ap.add_argument("--password", default=None, help="falls back to $DEMO_PASSWORD")
    ap.add_argument("--fast", action="store_true", help="skip narration pauses (for rehearsal)")
    ap.add_argument("--skip-novelty", action="store_true")
    args = ap.parse_args()

    import os
    password = args.password or os.environ.get("DEMO_PASSWORD")
    if not password:
        print("ERROR: pass --password or set $env:DEMO_PASSWORD first.", file=sys.stderr)
        return 1

    print(BANNER)
    with httpx.Client(base_url=args.api_url, timeout=15) as client:
        try:
            r = client.post("/auth/login", json={"username": args.user, "password": password})
            r.raise_for_status()
        except httpx.HTTPError as e:
            print(f"ERROR: could not log in — is the backend running at {args.api_url}? ({e})",
                  file=sys.stderr)
            return 1
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        seen = {a["id"] for a in client.get("/alerts", headers=headers).json()}
        results = []

        for step in build_scenario():
            narrate(step["text"], 0 if args.fast else step["pause"])
            t0, resp = send(client, headers, step["payload"])
            if resp["status"] == "duplicate":
                print("    (already ingested — rerun with a later --observed offset or reset the demo db)")
                continue
            alert = wait_for_new_alert(client, headers, seen)
            if alert:
                seen.add(alert["id"])
                elapsed = time.perf_counter() - t0
                results.append((alert, elapsed))
                print(f"    -> Alert #{alert['id']}: {alert['severity'].upper()} "
                      f"({alert['risk_score']*100:.0f}% risk) visible after {elapsed:.2f}s "
                      f"[server latency {alert['latency_ms']:.0f}ms]")
            else:
                print("    -> No alert this step (risk stayed below threshold) — expected for early days.")

        if not args.skip_novelty:
            step = build_novelty_step()
            narrate(step["text"], 0 if args.fast else step["pause"])
            t0, resp = send(client, headers, step["payload"])
            if resp["status"] != "duplicate":
                alert = wait_for_new_alert(client, headers, seen)
                if alert:
                    seen.add(alert["id"])
                    tag = "UNRECOGNISED PATTERN" if alert["novel"] else alert["severity"].upper()
                    print(f"    -> Alert #{alert['id']}: {tag} flagged "
                          f"after {time.perf_counter()-t0:.2f}s")

        print("\n=========================================================")
        print(f"  Scenario complete. {len(results)} alert(s) from the flood sequence.")
        if results:
            avg_ms = sum(r[0]["latency_ms"] for r in results) / len(results)
            print(f"  Average server-side ingest->alert latency: {avg_ms:.0f}ms "
                  f"(target: <60,000ms)")
        print("=========================================================\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())