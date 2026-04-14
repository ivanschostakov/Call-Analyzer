import logging
from datetime import timedelta
from types import SimpleNamespace

import pytest
from fastapi.security import HTTPAuthorizationCredentials
from starlette.requests import Request

from conftest import event_records
from src.app.modules.auth.dependencies import get_current_user
from src.app.modules.auth.schemas import AuthTokensWithUserResponse, AuthUserRead, UserLoginPayload
from src.enums import UserRole


def build_request(path: str) -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": path,
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 12345),
        }
    )


@pytest.mark.asyncio
async def test_login_route_logs_redacted_payload(caplog, monkeypatch) -> None:
    from src.app.modules.auth import router as auth_router

    async def fake_get_login_user(payload, db):
        return SimpleNamespace(id=7, email="user@example.com")

    async def fake_build_auth_tokens_response(user, db):
        return AuthTokensWithUserResponse(
            access_token="access",
            refresh_token="refresh",
            session_id=5,
            user=AuthUserRead(
                id=user.id,
                email=user.email,
                name="Test",
                surname="User",
                role=UserRole.OWNER,
                is_active=True,
                is_verified=True,
            ),
        )

    async def fake_accept_employee_invitation_for_user(db, token, user):
        return None

    monkeypatch.setattr(auth_router, "get_login_user", fake_get_login_user)
    monkeypatch.setattr(auth_router, "build_auth_tokens_response", fake_build_auth_tokens_response)
    monkeypatch.setattr(auth_router, "accept_employee_invitation_for_user", fake_accept_employee_invitation_for_user)

    caplog.set_level(logging.INFO)
    payload = UserLoginPayload(email="user@example.com", password="supersecret", invitation_token="invite-token")
    response = await auth_router.login(payload=payload, request=build_request("/auth/login"), db=None)

    assert response.session_id == 5

    start_record = event_records(caplog, "auth.login.start")[0]
    assert start_record.event_fields["payload"]["password"] == "[REDACTED]"
    assert start_record.event_fields["payload"]["invitation_token"] == "[REDACTED]"


@pytest.mark.asyncio
async def test_get_current_user_logs_success_with_actor_context(caplog, monkeypatch) -> None:
    from config import ufa_now
    from src.app.modules.auth import dependencies as auth_dependencies

    monkeypatch.setattr(
        auth_dependencies,
        "decode_access_token",
        lambda token: {"sub": "9", "sid": "12", "type": "access"},
    )

    async def fake_get_user_session_by_id(db, session_id):
        return SimpleNamespace(id=session_id, user_id=9, revoked_at=None, expires_at=ufa_now() + timedelta(days=1))

    async def fake_get_user_by_id(db, user_id):
        return SimpleNamespace(id=user_id, is_active=True)

    monkeypatch.setattr(auth_dependencies, "get_user_session_by_id", fake_get_user_session_by_id)
    monkeypatch.setattr(auth_dependencies, "get_user_by_id", fake_get_user_by_id)

    caplog.set_level(logging.INFO)
    user = await get_current_user(
        request=build_request("/auth/me"),
        credentials=HTTPAuthorizationCredentials(scheme="Bearer", credentials="token"),
        db=None,
    )

    assert user.id == 9
    success_record = event_records(caplog, "auth.current_user.success")[0]
    assert success_record.event_fields["user_id"] == 9
    assert success_record.event_fields["session_id"] == 12
