from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class MentorMessageCreatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    thread_id: int | None = None
    company_id: int
    template_id: int
    analysis_ids: list[int] = Field(min_length=1)
    columns: list[str] | None = None
    prompt: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_prompt(self) -> "MentorMessageCreatePayload":
        if not self.prompt.strip():
            raise ValueError("prompt must not be blank")
        return self


class MentorMessageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    thread_id: int
    role: Literal["user", "assistant"]
    content: str
    analysis_ids: list[int]
    selected_columns: list[str]
    row_count: int
    summarized_row_count: int
    omitted_row_count: int
    created_at: datetime
    updated_at: datetime


class MentorThreadResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    owner_user_id: int
    company_id: int
    template_id: int | None
    title: str
    created_at: datetime
    updated_at: datetime


class MentorThreadDetailResponse(MentorThreadResponse):
    messages: list[MentorMessageResponse]


class MentorReplyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    thread: MentorThreadResponse
    user_message: MentorMessageResponse
    assistant_message: MentorMessageResponse
