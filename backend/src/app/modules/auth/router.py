from datetime import timedelta
import logging
from logging import getLogger
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from config import REFRESH_TOKEN_LIFETIME_DAYS, ufa_now
from src.app.observability import bind_log_context, log_exception, log_info, log_warning
from .dependencies import get_current_user
from .helpers import build_auth_tokens_response, get_login_user
from .security import create_access_token, create_refresh_token, hash_password, hash_refresh_token, verify_refresh_token
from .schemas import (
    AuthLogoutResponse,
    AuthRefreshResponse,
    AuthTokensWithUserResponse,
    AuthUserRead,
    UserLoginPayload,
    UserLogoutPayload,
    UserRefreshPayload,
    UserRegisterPayload,
)
from src.app.modules.employees.helpers import accept_employee_invitation_for_user, ensure_invitation_is_usable
from src.database import get_db
from src.database.crud import (
    create_user,
    get_employee_invitation_by_token,
    get_user_by_id,
    get_user_session_by_id,
    update_user_session,
)
from src.database.models import User
from src.database.schemas import UserCreate, UserSessionUpdate
from src.enums import UserRole

logger = logging.getLogger(__name__)
auth_router = APIRouter(prefix="/auth", tags=["auth"])

@auth_router.post("/register", response_model=AuthTokensWithUserResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: UserRegisterPayload, request: Request, db: AsyncSession = Depends(get_db)) -> AuthTokensWithUserResponse:
    log_info(logger, "auth.register.start", path=request.url.path, payload=payload.model_dump())
    if payload.invitation_token: ensure_invitation_is_usable(await get_employee_invitation_by_token(db, payload.invitation_token), str(payload.email))
    password_hash = hash_password(payload.password)

    user_create = UserCreate(
        email=payload.email,
        name=payload.name,
        surname=payload.surname,
        password_hash=password_hash,
        role=UserRole.EMPLOYEE if payload.invitation_token else UserRole.OWNER,
    )

    try: user = await create_user(db, user_create)
    except IntegrityError as e:
        log_exception(logger, "auth.register.conflict", email=str(payload.email))
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists",
        ) from e

    if payload.invitation_token: await accept_employee_invitation_for_user(db, token=payload.invitation_token, user=user)

    log_info(logger, "auth.register.success", user_id=user.id, email=user.email, invitation_token=payload.invitation_token)
    return await build_auth_tokens_response(user, db)


@auth_router.post("/login", response_model=AuthTokensWithUserResponse, status_code=status.HTTP_200_OK, summary="Email and password login")
async def login(payload: UserLoginPayload, request: Request, db: AsyncSession = Depends(get_db)) -> AuthTokensWithUserResponse:
    log_info(logger, "auth.login.start", path=request.url.path, payload=payload.model_dump())
    user = await get_login_user(payload, db)
    if payload.invitation_token: await accept_employee_invitation_for_user(db, token=payload.invitation_token, user=user)
    log_info(logger, "auth.login.success", user_id=user.id, email=user.email, invitation_token=payload.invitation_token)
    return await build_auth_tokens_response(user, db)

@auth_router.post("/refresh", response_model=AuthRefreshResponse, status_code=status.HTTP_200_OK)
async def refresh(payload: UserRefreshPayload, request: Request, db: AsyncSession = Depends(get_db)) -> AuthRefreshResponse:
    log_info(logger, "auth.refresh.start", path=request.url.path, session_id=payload.session_id)
    session = await get_user_session_by_id(db, payload.session_id)
    if not session:
        log_warning(logger, "auth.refresh.failed", reason="session_not_found", session_id=payload.session_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    if session.revoked_at is not None:
        log_warning(logger, "auth.refresh.failed", reason="session_revoked", session_id=session.id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has been revoked",
        )

    if session.expires_at <= ufa_now():
        log_warning(logger, "auth.refresh.failed", reason="refresh_expired", session_id=session.id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired",
        )

    ok = verify_refresh_token(payload.refresh_token, session.refresh_token_hash)
    if not ok:
        log_warning(logger, "auth.refresh.failed", reason="refresh_mismatch", session_id=session.id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    user = await get_user_by_id(db, session.user_id)
    if not user or not user.is_active:
        log_warning(logger, "auth.refresh.failed", reason="inactive_or_missing_user", session_id=session.id, user_id=session.user_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    bind_log_context(user_id=user.id, session_id=session.id)
    new_refresh_token = create_refresh_token()
    new_refresh_token_hash = hash_refresh_token(new_refresh_token)

    user_session_update = UserSessionUpdate(
        refresh_token_hash=new_refresh_token_hash,
        last_used_at=ufa_now(),
        expires_at=ufa_now() + timedelta(days=REFRESH_TOKEN_LIFETIME_DAYS)
    )

    await update_user_session(db, session, user_session_update)
    access_token = create_access_token(user_id=user.id, session_id=session.id)
    log_info(logger, "auth.refresh.success", user_id=user.id, session_id=session.id)

    return AuthRefreshResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        session_id=session.id,
    )

@auth_router.post("/logout", response_model=AuthLogoutResponse, status_code=status.HTTP_200_OK)
async def logout(payload: UserLogoutPayload, request: Request, db: AsyncSession = Depends(get_db)) -> AuthLogoutResponse:
    log_info(logger, "auth.logout.start", path=request.url.path, session_id=payload.session_id)
    session = await get_user_session_by_id(db, payload.session_id)
    if not session:
        log_warning(logger, "auth.logout.failed", reason="session_not_found", session_id=payload.session_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    ok = verify_refresh_token(payload.refresh_token, session.refresh_token_hash)
    if not ok:
        log_warning(logger, "auth.logout.failed", reason="refresh_mismatch", session_id=session.id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    bind_log_context(user_id=session.user_id, session_id=session.id)
    if session.revoked_at is None:
        user_session_update = UserSessionUpdate(revoked_at=ufa_now())
        await update_user_session(db, session, user_session_update)

    log_info(logger, "auth.logout.success", user_id=session.user_id, session_id=session.id)
    return AuthLogoutResponse(ok=True, message="Logged out successfully")


@auth_router.get("/me", response_model=AuthUserRead, status_code=status.HTTP_200_OK)
async def me(current_user: User = Depends(get_current_user)) -> AuthUserRead:
    log_info(logger, "auth.me.success", user_id=current_user.id, email=current_user.email)
    return AuthUserRead.model_validate(current_user)
