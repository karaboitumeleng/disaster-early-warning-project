import hashlib
import json
import time
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.events import DataIngested, EventBus
from app.repositories import AuditRepo, ReadingRepo
from app.schemas import WeatherReading


@dataclass(frozen=True)
class IngestResult:
    reading_hash: str
    duplicate: bool


def payload_hash(reading: WeatherReading) -> str:
    canonical = json.dumps(reading.model_dump(mode="json"), sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()


class IngestionService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession], bus: EventBus) -> None:
        self.session_factory = session_factory
        self.bus = bus

    async def ingest(self, reading: WeatherReading, actor: str) -> IngestResult:
        received = time.monotonic()
        digest = payload_hash(reading)
        async with self.session_factory() as s:
            is_new = await ReadingRepo(s).add_if_new(digest, reading)
            await AuditRepo(s).record(
                actor,
                "ingest.accepted" if is_new else "ingest.duplicate",
                {"hash": digest, "region": reading.region_id},
            )
        if is_new:  # idempotent: duplicates never re-trigger prediction or alerts
            self.bus.publish(DataIngested(reading, digest, received))
        return IngestResult(digest, duplicate=not is_new)