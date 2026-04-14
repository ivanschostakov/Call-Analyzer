from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class EmployeeInvitationCreate(BaseModel):
    company_id: int
    email: EmailStr


class EmployeeInvitationAccept(BaseModel):
    token: str = Field(min_length=1)


class EmployeeInvitationRead(BaseModel):
    id: int
    company_id: int
    company_name: str
    email: str
    invited_by_user_id: int | None
    invited_by_display_name: str | None
    invited_by_email: str | None
    accepted_by_user_id: int | None
    accepted_by_display_name: str | None
    accepted_by_email: str | None
    accepted_at: datetime | None
    expires_at: datetime
    status: str
    created_at: datetime
    updated_at: datetime
