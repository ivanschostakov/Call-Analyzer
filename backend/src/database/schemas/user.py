from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from src.enums import UserRole


class UserBase(BaseModel):
    email: EmailStr
    name: str
    surname: str
    phone_number: str | None = None
    is_active: bool = True
    is_verified: bool = False
    last_active_at: datetime | None = None
    role: UserRole = UserRole.OWNER


class UserCreate(UserBase):
    password_hash: str


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    name: str | None = None
    surname: str | None = None
    phone_number: str | None = None
    is_active: bool | None = None
    is_verified: bool | None = None
    last_active_at: datetime | None = None
    role: UserRole | None = None
    password_hash: str | None = None


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
