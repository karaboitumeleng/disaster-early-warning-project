from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration comes from environment variables / .env. No secrets in code."""

    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    app_env: str = "dev"
    database_url: str = "sqlite+aiosqlite:///./ewsa.db"
    jwt_secret: str = Field(min_length=32)  # required: startup fails without it
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    cors_origins: str = "http://localhost:5173"
    alert_threshold: float = Field(default=0.6, ge=0, le=1)
    max_payload_bytes: int = 1_000_000
    demo_password: str | None = None
    models_dir: str = "../models"
    tiles_dir: str = "../data/tiles"
    use_torch_model: bool = True

    @property
    def origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]