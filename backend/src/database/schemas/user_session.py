from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserSessionCreate(BaseModel):
    user_id: int
    refresh_token_hash: str
    expires_at: datetime | None = None
    revoked_at: datetime | None = None
    last_used_at: datetime | None = None
    user_agent: str | None = None
    ip_address: str | None = None


class UserSessionUpdate(BaseModel):
    refresh_token_hash: str | None = None
    expires_at: datetime | None = None
    revoked_at: datetime | None = None
    last_used_at: datetime | None = None
    user_agent: str | None = None
    ip_address: str | None = None


class UserSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    refresh_token_hash: str
    expires_at: datetime
    revoked_at: datetime | None
    last_used_at: datetime | None
    user_agent: str | None
    ip_address: str | None
    created_at: datetime
    updated_at: datetime
