# CNN-LSTM in the live alert path

Status: written, NOT yet run or measured. Do not treat any statement here as evidence.

## Flow
    POST /ingest/weather -> reading stored -> DataIngested
    PredictionService:
      active model has predict_sequence?
        yes -> load up to 45 days of stored readings for the region (HistoryRepo)
               -> TorchPredictor.predict_sequence (in a worker thread, guarded by a lock)
               -> None (too little history) or exception -> StatisticalBaselinePredictor
        no  -> model.predict(...)
      -> audit record -> AlertService (threshold, severity, WebSocket push)

## How the input window is built (must match notebooks 03/04)
- One value per UTC day: the last reading of that day (multi-station data is not averaged).
- 14-day window; up to 2 absent days tolerated (rainfall 0, other variables carried forward,
  missing flags 1, confidence reduced). More than 2 absent days -> baseline fallback.
- API (antecedent precipitation) recomputed over up to 45 days; with less history it is
  underestimated slightly.
- Tile: data/tiles/<REGION>.npy, shape (4,16,16), raw (unnormalised). Missing tile or satellite
  feed down => blank (mean) tile, degraded=true. Notebook 04 trains with 20% tile dropout so
  that input is in-distribution. Reported test metrics use full tiles only, so degraded-mode
  accuracy is UNMEASURED.
- Statics come from models/preprocessing.json (region_statics), written by notebook 03.

## Scores
- risk_score is the model probability rescaled so its F1-tuned threshold maps to ALERT_THRESHOLD.
  This is monotone rescaling, not calibration; severity bands (0.75/0.9) are therefore arbitrary.
- confidence = 1 - 4 x MC-dropout std, minus 0.05 per absent day and 0.10 without a tile,
  halved when novel. A heuristic, not a calibrated interval.
- Explanations are feature-occlusion deltas in logit space (feature replaced by its training
  mean), top 5. They are attributions of this model, not causal statements.
- Novelty = envelope check OR autoencoder error above 1.5 x its 99th-percentile training error.

## Safety controls
- torch.load(weights_only=True); artefacts verified against models/manifest.json
  (python scripts/register_model.py after every training run).
- Outside APP_ENV=dev: manifest required, models trained on synthetic data refused.
- Any load failure keeps the API up on the baseline; /health/ready shows the active version.
- The Analytics overlay calls TorchPredictor.predict, which delegates to the baseline.

## Try it
    pip install -r backend/requirements-ml.txt
    python scripts/train_all.py            # retrain: notebook 04 now uses tile dropout
    python scripts/register_model.py
    make run ; python scripts/seed_history.py ; python scripts/measure_latency.py
The alert's model_version in the UI shows cnn-lstm-<hash>-<kind> when the model handled it.
Record measured latency in docs/PERFORMANCE.md (server latency now includes DB history + inference).
