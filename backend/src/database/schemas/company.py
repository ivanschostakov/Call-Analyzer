from datetime import date
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CompanyBase(BaseModel):
    owner_id: int
    name: str
    description: str | None = None


class CompanyCreate(CompanyBase):
    pass


class CompanyUpdate(BaseModel):
    owner_id: int | None = None
    name: str | None = None
    description: str | None = None
    transcription_hint_prompt: str | None = None
    report_summary_questions: list[str] | None = None
    vector_store_id: str | None = None
    beeline_api_token: str | None = None
    beeline_auto_export_enabled: bool | None = None
    beeline_auto_analysis_template_id: int | None = None
    beeline_last_sync_target_date: date | None = None
    beeline_last_sync_started_at: datetime | None = None
    beeline_last_sync_finished_at: datetime | None = None
    beeline_last_sync_status: str | None = None
    beeline_last_sync_error: str | None = None
    beeline_last_auto_sync_target_date: date | None = None
    beeline_last_auto_sync_started_at: datetime | None = None
    beeline_last_auto_sync_finished_at: datetime | None = None
    beeline_last_auto_sync_status: str | None = None
    beeline_last_auto_sync_error: str | None = None


class CompanyRead(CompanyBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    transcription_hint_prompt: str | None = None
    report_summary_questions: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
