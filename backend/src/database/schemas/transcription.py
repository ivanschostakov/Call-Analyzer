from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.enums import TranscriptionStatus


class TranscriptionSegmentRead(BaseModel):
    start: float
    end: float
    text: str


class TranscriptionCreate(BaseModel):
    company_id: int
    uploaded_by_user_id: int
    detected_employee_user_id: int | None = None
    file_id: str
    original_filename: str
    source_path: str
    file_path: str
    status: TranscriptionStatus = TranscriptionStatus.UPLOADED
    language: str | None = None
    text: str | None = None
    segments: list[TranscriptionSegmentRead] = Field(default_factory=list)
    error_message: str | None = None
    call_started_at: datetime | None = None
    transcribed_at: datetime | None = None


class TranscriptionUpdate(BaseModel):
    uploaded_by_user_id: int | None = None
    detected_employee_user_id: int | None = None
    original_filename: str | None = None
    source_path: str | None = None
    file_path: str | None = None
    status: TranscriptionStatus | None = None
    language: str | None = None
    text: str | None = None
    segments: list[TranscriptionSegmentRead] | None = None
    error_message: str | None = None
    call_started_at: datetime | None = None
    transcribed_at: datetime | None = None


class TranscriptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    uploaded_by_user_id: int
    detected_employee_user_id: int | None
    file_id: str
    original_filename: str
    status: TranscriptionStatus
    language: str | None
    text: str | None
    segments: list[TranscriptionSegmentRead]
    error_message: str | None
    call_started_at: datetime | None
    transcribed_at: datetime | None
    created_at: datetime
    updated_at: datetime
