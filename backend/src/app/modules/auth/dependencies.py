import logging

from fastapi import Depends, HTTPException
from fastapi import Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from config import ufa_now
from src.app.observability import bind_log_context, log_info, log_warning
from src.app.modules.auth.security.access import decode_access_token
from src.database import get_db
from src.database.crud import get_user_by_id, get_user_session_by_id
from src.database.models import User

bearer_scheme = HTTPBearer(auto_error=False)
logger = logging.getLogger(__name__)


def unauthorized_exception(detail: str = "Could not validate credentials") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        log_warning(logger, "auth.current_user.failed", reason="missing_or_invalid_scheme", path=request.url.path)
        raise unauthorized_exception()

    payload = decode_access_token(credentials.credentials)
    if payload is None or payload.get("type") != "access":
        log_warning(logger, "auth.current_user.failed", reason="invalid_access_token", path=request.url.path)
        raise unauthorized_exception()

    try:
        user_id = int(payload["sub"])
        session_id = int(payload["sid"])
    except (KeyError, TypeError, ValueError):
        log_warning(logger, "auth.current_user.failed", reason="malformed_access_payload", path=request.url.path)
        raise unauthorized_exception() from None

    bind_log_context(user_id=user_id, session_id=session_id)

    user_session = await get_user_session_by_id(db, session_id)
    if user_session is None or user_session.user_id != user_id or user_session.revoked_at is not None:
        log_warning(logger, "auth.current_user.failed", reason="session_missing_or_revoked", user_id=user_id, session_id=session_id)
        raise unauthorized_exception()
    if user_session.expires_at <= ufa_now():
        log_warning(logger, "auth.current_user.failed", reason="session_expired", user_id=user_id, session_id=session_id)
        raise unauthorized_exception("Session has expired")

    user = await get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        log_warning(logger, "auth.current_user.failed", reason="inactive_or_missing_user", user_id=user_id, session_id=session_id)
        raise unauthorized_exception()

    log_info(logger, "auth.current_user.success", user_id=user.id, session_id=session_id, path=request.url.path)

    return user
