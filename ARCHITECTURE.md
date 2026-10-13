# Architecture (vertical slice)

Layered, event-driven **modular monolith**: one deployable, clean module boundaries, so any layer
can later be extracted into a service.

| Layer | Module | Rule |
|---|---|---|
| Presentation | `frontend/` | Talks to the API only (REST + WebSocket) |
| API | `backend/app/api/` | Validation, auth, RBAC, rate limit. Never imports model code |
| Application | `backend/app/application/` | Use-case services (Ingestion, Prediction, Alert) |
| ML | `backend/app/ml/` | `Predictor` protocol, registry with fallback, novelty check |
| Data | `backend/app/repositories.py`, `models.py` | Repository pattern, ORM only (no raw SQL) |

## Why event-driven ingestion
`POST /ingest/weather` persists the reading, publishes `DataIngested` and returns 202 immediately.
Prediction and alerting run as background tasks, so a slow model cannot block the API, and a
failed handler is logged without crashing anything (fault isolation). Alert latency is recorded
per alert (`latency_ms`) as evidence for `docs/PERFORMANCE.md`.

## Sequence
    Client -> API: POST /ingest/weather (JWT, analyst|admin)
    API -> IngestionService: hash payload, insert if new (idempotent)
    IngestionService -> EventBus: DataIngested
    API -> Client: 202
    EventBus -> PredictionService: predict via Predictor (no satellite => degraded mode)
    PredictionService -> AlertService: risk >= threshold or novel input
    AlertService -> DB: insert alert (unique per reading hash => no duplicate alerts)
    AlertService -> AlertHub: broadcast over WebSocket -> dashboard

## Model-service decoupling
`Predictor` is a Protocol. Today: `StatisticalBaselinePredictor`. Later: CNN-LSTM loaded from
`models/` through the same interface, with the baseline as the automatic fallback.

## OWML hooks
`ml/novelty.py` flags inputs outside the training envelope as "unrecognised pattern" alerts
instead of silently classifying them. It is a placeholder for an autoencoder-based detector.