from collections.abc import AsyncIterator, Awaitable, Callable

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.security import TokenData, decode_token

bearer = HTTPBearer(auto_error=True)


async def db_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.session_factory() as s:
        yield s


async def current_user(
    request: Request, creds: HTTPAuthorizationCredentials = Depends(bearer)
) -> TokenData:
    try:
        return decode_token(creds.credentials, request.app.state.settings)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from None


def require_roles(*roles: str) -> Callable[..., Awaitable[TokenData]]:
    async def dep(user: TokenData = Depends(current_user)) -> TokenData:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient role")
        return user

    return dep