from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.database.schemas import TranscriptionSegmentRead
from src.enums import TranscriptionStatus


class TranscriptionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    company_id: int
    uploaded_by_user_id: int
    uploaded_by_display_name: str | None = None
    uploaded_by_email: str | None = None
    detected_employee_user_id: int | None = None
    detected_employee_display_name: str | None = None
    detected_employee_email: str | None = None
    file_id: str
    original_filename: str
    status: TranscriptionStatus
    media_url: str
    language: str | None = None
    text: str | None = None
    segments: list[TranscriptionSegmentRead] = Field(default_factory=list)
    error_message: str | None = None
    is_favorite: bool = False
    call_started_at: datetime | None = None
    transcribed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class TranscriptionListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[TranscriptionResponse] = Field(default_factory=list)


class TranscriptionEmployeeAssignment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    employee_user_id: int | None = None


class TranscriptionDeleteResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    message: str
