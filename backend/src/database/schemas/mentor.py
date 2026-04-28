from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


MentorMessageRole = Literal["user", "assistant"]


class MentorThreadCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    owner_user_id: int
    company_id: int
    template_id: int | None = None
    openai_conversation_id: str | None = None
    title: str


class MentorThreadUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    template_id: int | None = None
    openai_conversation_id: str | None = None
    title: str | None = None


class MentorMessageCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    thread_id: int
    role: MentorMessageRole
    content: str
    analysis_ids: list[int] = Field(default_factory=list)
    selected_columns: list[str] = Field(default_factory=list)
    row_count: int = 0
    summarized_row_count: int = 0
    omitted_row_count: int = 0


class MentorMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    thread_id: int
    role: MentorMessageRole
    content: str
    analysis_ids: list[int] = Field(default_factory=list)
    selected_columns: list[str] = Field(default_factory=list)
    row_count: int
    summarized_row_count: int
    omitted_row_count: int
    created_at: datetime
    updated_at: datetime


class MentorThreadRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_user_id: int
    company_id: int
    template_id: int | None = None
    openai_conversation_id: str | None = None
    title: str
    created_at: datetime
    updated_at: datetime
