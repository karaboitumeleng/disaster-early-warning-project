from datetime import datetime, timedelta, timezone
from typing import Any

from pydantic import BaseModel, Field, field_validator

_ID = r"^[A-Za-z0-9_-]+$"


class WeatherReading(BaseModel):
    """Validated sensor payload. South Africa bounding box is enforced on coordinates."""

    station_id: str = Field(min_length=1, max_length=32, pattern=_ID)
    region_id: str = Field(min_length=1, max_length=32, pattern=_ID)
    observed_at: datetime
    lat: float = Field(ge=-35.0, le=-22.0)
    lon: float = Field(ge=16.0, le=33.0)
    rainfall_mm_24h: float = Field(ge=0, le=1000)
    river_level_m: float | None = Field(default=None, ge=0, le=50)
    soil_moisture: float | None = Field(default=None, ge=0, le=1)
    temperature_c: float | None = Field(default=None, ge=-20, le=55)
    humidity_pct: float | None = Field(default=None, ge=0, le=100)
    ndwi_mean: float | None = Field(default=None, ge=-1, le=1)  # satellite water index (optional)
    pressure_hpa: float | None = Field(default=None, ge=850, le=1100)
    wind_ms: float | None = Field(default=None, ge=0, le=80)

    @field_validator("observed_at")
    @classmethod
    def _utc_not_future(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        if v > datetime.now(timezone.utc) + timedelta(minutes=5):
            raise ValueError("observed_at is in the future")
        return v.astimezone(timezone.utc)

    def features(self) -> dict[str, float | None]:
        return {
            "rainfall_mm_24h": self.rainfall_mm_24h,
            "river_level_m": self.river_level_m,
            "soil_moisture": self.soil_moisture,
            "temperature_c": self.temperature_c,
            "humidity_pct": self.humidity_pct,
            "ndwi_mean": self.ndwi_mean,
        }


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=72)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


class AlertOut(BaseModel):
    id: int
    region_id: str
    severity: str
    disaster_type: str
    risk_score: float
    confidence: float
    degraded: bool
    novel: bool
    model_version: str
    explanation: list[dict[str, Any]]
    status: str
    handled_by: str | None
    latency_ms: float
    created_at: datetime


class RegionOut(BaseModel):
    id: str
    name: str
    province: str
    geojson: dict[str, Any]
    centroid_lat: float
    centroid_lon: float
    risk_score: float
    band: str  # "low" | "elevated" | "high" — never rely on colour alone
    degraded: bool
    novel: bool
    last_updated: datetime | None

class ReadingOut(BaseModel):
    observed_at: datetime
    rainfall_mm_24h: float | None = None
    river_level_m: float | None = None
    soil_moisture: float | None = None
    temperature_c: float | None = None
    humidity_pct: float | None = None


class ModelMetrics(BaseModel):
    available: bool
    dataset_version: str | None = None
    smart_target: float | None = None
    smart_target_met: bool | None = None
    models: dict[str, dict[str, Any]] | None = None
    real_data_only: dict[str, Any] | None = None
    novelty_detector: dict[str, Any] | None = None
    note: str | None = None
    active_model_version: str