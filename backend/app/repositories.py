from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Alert, AuditLog, Reading, Region, User
from app.schemas import WeatherReading


class UserRepo:
    def __init__(self, s: AsyncSession) -> None:
        self.s = s

    async def by_username(self, username: str) -> User | None:
        res = await self.s.execute(select(User).where(User.username == username))
        return res.scalar_one_or_none()

    async def add(self, username: str, password_hash: str, role: str) -> None:
        self.s.add(User(username=username, password_hash=password_hash, role=role))
        await self.s.commit()


class ReadingRepo:
    def __init__(self, s: AsyncSession) -> None:
        self.s = s

    async def add_if_new(self, payload_hash: str, reading: WeatherReading) -> bool:
        exists = await self.s.execute(select(Reading.id).where(Reading.payload_hash == payload_hash))
        if exists.first() is not None:
            return False
        self.s.add(
            Reading(
                payload_hash=payload_hash,
                region_id=reading.region_id,
                observed_at=reading.observed_at,
                payload=reading.model_dump(mode="json"),
            )
        )
        try:
            await self.s.commit()
        except IntegrityError:  # lost a race with an identical payload
            await self.s.rollback()
            return False
        return True
    async def has_any(self) -> bool:
        result = await self.s.execute(select(Reading.id).limit(1))
        return result.first() is not None

class AlertRepo:
    def __init__(self, s: AsyncSession) -> None:
        self.s = s

    async def add(self, alert: Alert) -> Alert | None:
        self.s.add(alert)
        try:
            await self.s.commit()
        except IntegrityError:  # alert for this reading already exists
            await self.s.rollback()
            return None
        return alert

    async def list(self, status: str | None, limit: int) -> list[Alert]:
        q = select(Alert).order_by(Alert.id.desc()).limit(limit)
        if status:
            q = q.where(Alert.status == status)
        return list((await self.s.execute(q)).scalars())

    async def get(self, alert_id: int) -> Alert | None:
        return await self.s.get(Alert, alert_id)

    async def set_status(self, alert: Alert, status: str, actor: str) -> Alert:
        alert.status, alert.handled_by = status, actor
        await self.s.commit()
        return alert


class AuditRepo:
    def __init__(self, s: AsyncSession) -> None:
        self.s = s

    async def record(self, actor: str, action: str, detail: dict[str, Any]) -> None:
        self.s.add(AuditLog(actor=actor, action=action, detail=detail))
        await self.s.commit()

class RegionRepo:
    def __init__(self, s: AsyncSession) -> None:
        self.s = s

    async def list_all(self) -> list[Region]:
        return list((await self.s.execute(select(Region))).scalars())

    async def seed_if_empty(self, regions: list[Region]) -> None:
        if (await self.s.execute(select(Region.id).limit(1))).first() is not None:
            return
        self.s.add_all(regions)
        await self.s.commit()

    async def latest_alert_for(self, region_id: str) -> Alert | None:
        q = (
            select(Alert)
            .where(Alert.region_id == region_id)
            .order_by(Alert.created_at.desc())
            .limit(1)
        )
        return (await self.s.execute(q)).scalar_one_or_none()   

    async def recent(self, region_id: str, limit: int) -> list[Reading]:
        q = (
            select(Reading)
            .where(Reading.region_id == region_id)
            .order_by(Reading.observed_at.desc())
            .limit(limit)
        )
        rows = list((await self.s.execute(q)).scalars())
        return list(reversed(rows))     