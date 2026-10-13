# Presentation demo — run sheet

## ~15 minutes before you present

```powershell
# Terminal 1 — backend
cd backend
& .\.venv\Scripts\Activate.ps1
uvicorn app.main:create_app --factory --reload --port 8000


```powershell
# Terminal 2 — frontend
cd C:\Users\Admin\disaster-early-warning\frontend
npm run dev


Open `http://localhost:5173` in the browser you'll be sharing/projecting. Log in as
`analyst` with the `DEMO_PASSWORD` from your `.env`. Leave it on the **Risk map** tab —
that's where you'll start.

**Do one full rehearsal run first** (see "Rehearsal" below) so the timing feels natural and
you're not seeing anything for the first time live.

## During the presentation

```powershell
# Terminal 3 — the scenario
cd disaster-early-warning
$env:DEMO_PASSWORD = "<your value>"
python scripts\demo_scenario.py
```

The script narrates each step in the terminal with a pause before sending — talk over the
pause, then let the dashboard update after it fires. Suggested talk track, matched to each
step's console output:

1. **Day -3 (calm):** "This is eThekwini right now — normal conditions, sitting green on the
   map." Point at the Risk Map tab.
2. **Day -2 (rain arrives):** "SAWS station data is flowing in. Watch the band." Point at the
   region on the map ticking to amber/elevated.
3. **Day -1 (intensifying):** Switch to the **Live alerts** tab if a warning fires — show the
   "why this alert" expandable explanation (top contributing features).
4. **Day 0 (the flood):** This is the moment. It mirrors the real 11 April 2022 KZN event.
   A CRITICAL alert should appear within a couple of seconds — point out the pulsing red
   marker on the map, the persistent red banner, and read out the measured latency the
   script prints (this is your evidence for the <60s objective, live).
   - Optionally click **Acknowledge** then **Resolve** on the alert card to show the officer
     workflow.
5. **Novelty step:** Switch back to the terminal, then the dashboard. "Now watch what happens
   when the system sees something it's never been trained on" — the alert should say
   "Unrecognised pattern" rather than confidently guessing a disaster type. This is the
   Open World ML hook from the spec.

## If something doesn't fire an alert
Check the terminal output — it prints "No alert this step" for the early calm/light-rain days,
which is expected (they're meant to stay under the threshold). If the Day 0 step doesn't fire,
the backend log (Terminal 1) will show the exception; that's your fallback talking point —
"and this is exactly why we log every prediction to the audit trail."

## Rehearsal (run this beforehand, as many times as you want)

```powershell
python scripts\demo_scenario.py --fast
```

`--fast` skips the narration pauses so you can quickly check everything fires correctly.

## Resetting between rehearsals or before the real run

```powershell
.\scripts\wipe_demo_db.ps1
```

Then restart the backend (the script prints the exact command). This wipes all demo alerts so
you start from a clean, empty dashboard — same as a first-time viewer will see.

## Honest caveats to have ready if asked
- The CNN-LSTM only activates if `models/cnn_lstm.keras` exists (i.e., the notebooks were run).
  Without it, predictions come from the documented statistical baseline — say so if asked
  which model is live; `GET /models/metrics` on the Model Performance tab shows which one is
  active.
- Region boundaries on the map are simplified placeholder rectangles, not verified municipal
  geometry — mention this if anyone zooms in and asks about the shapes.
- Satellite imagery isn't wired in yet — every prediction shows "reduced confidence" for that
  reason, which is itself a good demo of the graceful-degradation requirement.