import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.alerts import AlertService
from app.events import DataIngested
from app.ml.predictor import Features, ModelRegistry
from app.repositories import AuditRepo, ReadingRepo

log = logging.getLogger(__name__)


class PredictionService:
    def __init__(
        self,
        registry: ModelRegistry,
        alerts: AlertService,
        session_factory: async_sessionmaker[AsyncSession],
        lookback: int = 10,
    ) -> None:
        self.registry = registry
        self.alerts = alerts
        self.session_factory = session_factory
        self.lookback = lookback

    async def on_data_ingested(self, event: DataIngested) -> None:
        features = event.reading.features()
        async with self.session_factory() as s:
            history_rows = await ReadingRepo(s).recent(event.reading.region_id, self.lookback)
        history: list[Features] = [r.payload for r in history_rows[:-1]]  # exclude the row just added

        pred = self.registry.predict_with_fallback(event.reading.region_id, features, history)

        async with self.session_factory() as s:
            await AuditRepo(s).record(
                "system", "prediction",
                {"region": pred.region_id, "score": pred.risk_score, "model": pred.model_version,
                 "degraded": pred.degraded, "novel": pred.novel},
            )
        await self.alerts.evaluate(pred, event.reading_hash, event.received_at)
        log.info("prediction complete", extra={"ctx": {"region": pred.region_id,
                                                        "score": pred.risk_score}})