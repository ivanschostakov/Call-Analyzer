from pydantic import BaseModel, EmailStr, Field

class UserLoginPayload(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    invitation_token: str | None = Field(default=None, min_length=1)
