from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.database.schemas import TranscriptionSegmentRead
from src.enums import TranscriptionStatus


class UploadItemResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

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
    error_message: str | None = None
    is_favorite: bool = False
    call_started_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class UploadAudioResponse(UploadItemResponse):
    pass


class UploadListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[UploadItemResponse] = Field(default_factory=list)


class UploadDeleteResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    message: str
