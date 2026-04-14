from typing import Literal

from pydantic import BaseModel, ConfigDict

from src.enums import UserRole


class AuthUserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    name: str
    surname: str
    role: UserRole
    is_active: bool
    is_verified: bool


class AuthTokensBase(BaseModel):
    access_token: str
    refresh_token: str
    session_id: int
    token_type: Literal["bearer"] = "bearer"


class AuthTokensWithUserResponse(AuthTokensBase):
    user: AuthUserRead


class AuthRefreshResponse(AuthTokensBase):
    pass


class AuthLogoutResponse(BaseModel):
    ok: bool
    message: str
