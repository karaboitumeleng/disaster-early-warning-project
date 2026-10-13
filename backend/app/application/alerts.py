import time
from datetime import timezone

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.hub import AlertHub
from app.ml.predictor import Prediction
from app.models import Alert
from app.repositories import AlertRepo, AuditRepo
from app.schemas import AlertOut


def severity_for(score: float, novel: bool) -> str:
    if novel:
        return "watch"
    if score >= 0.9:
        return "critical"
    if score >= 0.75:
        return "warning"
    return "watch"


def alert_to_out(a: Alert) -> AlertOut:
    created = a.created_at if a.created_at.tzinfo else a.created_at.replace(tzinfo=timezone.utc)
    return AlertOut(
        id=a.id, region_id=a.region_id, severity=a.severity, disaster_type=a.disaster_type,
        risk_score=a.risk_score, confidence=a.confidence, degraded=a.degraded, novel=a.novel,
        model_version=a.model_version, explanation=a.explanation, status=a.status,
        handled_by=a.handled_by, latency_ms=a.latency_ms, created_at=created,
    )


class AlertService:
    def __init__(
        self, session_factory: async_sessionmaker[AsyncSession], hub: AlertHub, threshold: float
    ) -> None:
        self.session_factory = session_factory
        self.hub = hub
        self.threshold = threshold

    async def evaluate(
        self, pred: Prediction, reading_hash: str, received_at: float
    ) -> AlertOut | None:
        if not (pred.novel or pred.risk_score >= self.threshold):
            return None
        alert = Alert(
            reading_hash=reading_hash,
            region_id=pred.region_id,
            severity=severity_for(pred.risk_score, pred.novel),
            disaster_type=pred.disaster_type,
            risk_score=pred.risk_score,
            confidence=pred.confidence,
            degraded=pred.degraded,
            novel=pred.novel,
            model_version=pred.model_version,
            explanation=[{"feature": f, "contribution": c} for f, c in pred.top_features],
            latency_ms=round((time.monotonic() - received_at) * 1000, 1),
        )
        async with self.session_factory() as s:
            saved = await AlertRepo(s).add(alert)
            if saved is None:  # already alerted for this reading
                return None
            await AuditRepo(s).record(
                "system", "alert.issued", {"alert_id": saved.id, "severity": saved.severity}
            )
        out = alert_to_out(saved)
        await self.hub.broadcast(out.model_dump(mode="json"))
        return out