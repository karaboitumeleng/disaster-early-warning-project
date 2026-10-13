import asyncio
from typing import Any

from pathlib import Path
import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user, db_session, require_roles
from app.application.alerts import alert_to_out
from app.repositories import AlertRepo, AuditRepo, UserRepo
from app.schemas import AlertOut, LoginRequest, RegionOut, TokenResponse, WeatherReading
from app.security import TokenData, create_token, decode_token, hash_password, verify_password
from app.schemas import ModelMetrics, ReadingOut
from app.ml.metrics_loader import load_model_metrics
from app.repositories import ReadingRepo

router = APIRouter()
_DUMMY_HASH = hash_password("dummy-password")  # equalises timing for unknown usernames
_WRITERS = ("admin", "analyst")


# ---- auth ----
@router.post("/auth/login", response_model=TokenResponse)
async def login(
    body: LoginRequest, request: Request, s: AsyncSession = Depends(db_session)
) -> TokenResponse:
    ip = request.client.host if request.client else "unknown"
    if not request.app.state.login_limiter.allow(ip):
        raise HTTPException(status_code=429, detail="Too many login attempts")
    user = await UserRepo(s).by_username(body.username)
    ok = verify_password(body.password, user.password_hash if user else _DUMMY_HASH) and user
    await AuditRepo(s).record(
        body.username, "login.success" if ok else "login.failure", {"ip": ip}
    )
    if not user or not ok:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token(user.username, user.role, request.app.state.settings)
    return TokenResponse(access_token=token, role=user.role)


# ---- ingestion ----
@router.post("/ingest/weather", status_code=202)
async def ingest_weather(
    reading: WeatherReading, request: Request, user: TokenData = Depends(require_roles(*_WRITERS))
) -> dict[str, Any]:
    result = await request.app.state.ingestion.ingest(reading, actor=user.sub)
    return {"status": "duplicate" if result.duplicate else "accepted",
            "reading_hash": result.reading_hash}


# ---- alerts ----
@router.get("/alerts", response_model=list[AlertOut])
async def list_alerts(
    status: str | None = Query(default=None, pattern="^(open|acknowledged|resolved)$"),
    limit: int = Query(default=100, ge=1, le=500),
    _: TokenData = Depends(current_user),
    s: AsyncSession = Depends(db_session),
) -> list[AlertOut]:
    return [alert_to_out(a) for a in await AlertRepo(s).list(status, limit)]


async def _transition(
    alert_id: int, target: str, allowed_from: set[str], user: TokenData, s: AsyncSession
) -> AlertOut:
    repo = AlertRepo(s)
    alert = await repo.get(alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    if alert.status not in allowed_from:
        raise HTTPException(status_code=409, detail=f"Cannot move {alert.status} -> {target}")
    alert = await repo.set_status(alert, target, user.sub)
    await AuditRepo(s).record(user.sub, f"alert.{target}", {"alert_id": alert_id})
    return alert_to_out(alert)


@router.post("/alerts/{alert_id}/ack", response_model=AlertOut)
async def ack_alert(
    alert_id: int, user: TokenData = Depends(require_roles(*_WRITERS)),
    s: AsyncSession = Depends(db_session),
) -> AlertOut:
    return await _transition(alert_id, "acknowledged", {"open"}, user, s)


@router.post("/alerts/{alert_id}/resolve", response_model=AlertOut)
async def resolve_alert(
    alert_id: int, user: TokenData = Depends(require_roles(*_WRITERS)),
    s: AsyncSession = Depends(db_session),
) -> AlertOut:
    return await _transition(alert_id, "resolved", {"open", "acknowledged"}, user, s)


# ---- health ----
@router.get("/health/live")
async def live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
async def ready(request: Request, s: AsyncSession = Depends(db_session)) -> dict[str, Any]:
    checks: dict[str, str] = {}
    try:
        await s.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "down"
    checks["model"] = request.app.state.registry.active().version
    checks["satellite_feed"] = "up" if request.app.state.feeds.is_up("satellite") else "down"
    if checks["database"] != "ok":
        raise HTTPException(status_code=503, detail=checks)
    return {"status": "ready", "checks": checks}


@router.get("/health")
async def health(request: Request, s: AsyncSession = Depends(db_session)) -> dict[str, Any]:
    return await ready(request, s)


# ---- websocket ----
@router.websocket("/ws/alerts")
async def ws_alerts(ws: WebSocket) -> None:
    settings = ws.app.state.settings
    origin = ws.headers.get("origin")
    if origin and origin not in settings.origins:
        await ws.close(code=4403)
        return
    await ws.accept()
    try:  # token goes in the first message, not the URL (URLs end up in logs)
        first = await asyncio.wait_for(ws.receive_json(), timeout=5)
        decode_token(first["token"], settings)
    except (Exception, jwt.PyJWTError):
        await ws.close(code=4401)
        return
    hub = ws.app.state.hub
    hub.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        hub.disconnect(ws)

@router.get("/regions", response_model=list[RegionOut])
async def list_regions(
    request: Request, _: TokenData = Depends(current_user)
) -> list[RegionOut]:
    return await request.app.state.riskmap.get_regions()        

@router.get("/regions/{region_id}/readings", response_model=list[ReadingOut])
async def region_readings(
    region_id: str, limit: int = Query(default=120, ge=1, le=500),
    _: TokenData = Depends(current_user), s: AsyncSession = Depends(db_session),
) -> list[ReadingOut]:
    rows = await ReadingRepo(s).recent(region_id, limit)
    return [ReadingOut(observed_at=r.observed_at, **{k: v for k, v in r.payload.items()
            if k in {"rainfall_mm_24h", "river_level_m", "soil_moisture", "temperature_c", "humidity_pct"}})
            for r in rows]


@router.get("/models/metrics", response_model=ModelMetrics)
async def model_metrics(request: Request, _: TokenData = Depends(current_user)) -> ModelMetrics:
    models_dir = Path(__file__).resolve().parents[3] / "models"
    return load_model_metrics(models_dir, request.app.state.registry.active().version)