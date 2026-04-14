from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from src.enums import UserRole


class EmployeeBase(BaseModel):
    user_id: int
    company_id: int
    manager_user_id: int | None = None


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeUpdate(BaseModel):
    user_id: int | None = None
    company_id: int | None = None
    manager_user_id: int | None = None
    user_role: UserRole | None = None


class EmployeeRead(EmployeeBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_role: UserRole | None = None
    user_display_name: str | None = None
    user_email: EmailStr | None = None
    manager_display_name: str | None = None
    manager_email: EmailStr | None = None
    created_at: datetime
    updated_at: datetime
