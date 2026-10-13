from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Reading


class HistoryRepo:
    """Read-only access to stored readings for building model input windows."""

    def __init__(self, s: AsyncSession) -> None:
        self.s = s

    async def payloads(
        self, region_id: str, since: datetime, until: datetime, limit: int = 5000
    ) -> list[dict[str, Any]]:
        q = (
            select(Reading)
            .where(
                Reading.region_id == region_id,
                Reading.observed_at >= since,
                Reading.observed_at <= until,
            )
            .order_by(Reading.observed_at)
            .limit(limit)
        )
        return [r.payload for r in (await self.s.execute(q)).scalars()]
