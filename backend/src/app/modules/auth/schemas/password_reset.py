from pydantic import BaseModel, EmailStr, Field


class PasswordResetRequestPayload(BaseModel):
    email: EmailStr


class PasswordResetConfirmPayload(BaseModel):
    token: str = Field(min_length=32, max_length=256)
    new_password: str = Field(min_length=8, max_length=128)


class PasswordResetResponse(BaseModel):
    ok: bool = True
    message: str
