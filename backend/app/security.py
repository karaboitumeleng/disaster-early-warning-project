import time
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import Settings

ROLES = {"admin", "analyst", "viewer"}


def _b(password: str) -> bytes:
    return password.encode()[:72]  # bcrypt input limit


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_b(password), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(_b(password), hashed.encode())


@dataclass(frozen=True)
class TokenData:
    sub: str
    role: str


def create_token(sub: str, role: str, settings: Settings) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    return jwt.encode(
        {"sub": sub, "role": role, "exp": exp}, settings.jwt_secret, algorithm=settings.jwt_algorithm
    )


def decode_token(token: str, settings: Settings) -> TokenData:
    """Raises jwt.PyJWTError on any problem (expired, tampered, wrong alg, bad claims)."""
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    sub, role = payload.get("sub"), payload.get("role")
    if not isinstance(sub, str) or role not in ROLES:
        raise jwt.InvalidTokenError("bad claims")
    return TokenData(sub=sub, role=role)


class SlidingWindowLimiter:
    """Small in-memory limiter (per-process). Replace with Redis if ever scaled out."""

    def __init__(self, limit: int, window_s: float) -> None:
        self.limit, self.window_s = limit, window_s
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        q = self._hits[key]
        while q and now - q[0] > self.window_s:
            q.popleft()
        if len(q) >= self.limit:
            return False
        q.append(now)
        return True