from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(128))
    role: Mapped[str] = mapped_column(String(16))


class Reading(Base):
    __tablename__ = "readings"
    id: Mapped[int] = mapped_column(primary_key=True)
    payload_hash: Mapped[str] = mapped_column(String(64), unique=True)  # idempotency key
    region_id: Mapped[str] = mapped_column(String(32), index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Alert(Base):
    __tablename__ = "alerts"
    id: Mapped[int] = mapped_column(primary_key=True)
    reading_hash: Mapped[str] = mapped_column(String(64), unique=True)  # one alert per reading
    region_id: Mapped[str] = mapped_column(String(32), index=True)
    severity: Mapped[str] = mapped_column(String(16))
    disaster_type: Mapped[str] = mapped_column(String(32))
    risk_score: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float)
    degraded: Mapped[bool] = mapped_column(Boolean)
    novel: Mapped[bool] = mapped_column(Boolean)
    model_version: Mapped[str] = mapped_column(String(32))
    explanation: Mapped[list[Any]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(16), default="open")
    handled_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    latency_ms: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    actor: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(48), index=True)
    detail: Mapped[dict[str, Any]] = mapped_column(JSON)

class Region(Base):
    __tablename__ = "regions"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)  # e.g. KZN-ETHEKWINI
    name: Mapped[str] = mapped_column(String(64))
    province: Mapped[str] = mapped_column(String(32))
    geojson: Mapped[dict[str, Any]] = mapped_column(JSON)  # placeholder polygon, see DATA_SOURCES.md
    centroid_lat: Mapped[float] = mapped_column(Float)
    centroid_lon: Mapped[float] = mapped_column(Float)