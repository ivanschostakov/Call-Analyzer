import logging

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from .schemas import UserLoginPayload, AuthUserRead, AuthTokensWithUserResponse
from .security import verify_password, create_access_token, hash_refresh_token, create_refresh_token
from src.app.observability import bind_log_context, log_info, log_warning
from src.database.crud import get_user_by_email, create_user_session
from src.database.models import User
from src.database.schemas import UserSessionCreate

logger = logging.getLogger(__name__)


async def build_auth_tokens_response(user: User, db: AsyncSession) -> AuthTokensWithUserResponse:
    refresh_token = create_refresh_token()
    refresh_token_hash = hash_refresh_token(refresh_token)

    user_session_create = UserSessionCreate(
        user_id=user.id,
        refresh_token_hash=refresh_token_hash,
    )
    session = await create_user_session(db, user_session_create)
    access_token = create_access_token(user_id=user.id, session_id=session.id)
    bind_log_context(user_id=user.id, session_id=session.id)
    log_info(logger, "auth.tokens.created", user_id=user.id, session_id=session.id)

    return AuthTokensWithUserResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        session_id=session.id,
        user=AuthUserRead.model_validate(user),
    )


async def get_login_user(payload: UserLoginPayload, db: AsyncSession) -> User:
    log_info(logger, "auth.login.lookup", email=str(payload.email), invitation_token=payload.invitation_token)
    user = await get_user_by_email(db, str(payload.email))
    if not user or not user.is_active or not verify_password(payload.password, user.password_hash):
        log_warning(logger, "auth.login.failed", email=str(payload.email), reason="invalid_credentials")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    log_info(logger, "auth.login.user_validated", user_id=user.id, email=user.email)
    return user
