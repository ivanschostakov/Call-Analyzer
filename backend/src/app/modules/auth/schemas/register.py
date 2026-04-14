from pydantic import BaseModel, Field, EmailStr

from src.database.limits import PERSON_NAME_MAX_LENGTH


class UserRegisterPayload(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=100)
    name: str = Field(min_length=1, max_length=PERSON_NAME_MAX_LENGTH)
    surname: str = Field(min_length=1, max_length=PERSON_NAME_MAX_LENGTH)
    invitation_token: str | None = Field(default=None, min_length=1)
