from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class CompanyCreatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    description: str | None = None


class CompanyUpdatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    description: str | None = None
    transcription_hint_prompt: str | None = None
    report_summary_questions: list[str] | None = None


class CompanyVectorStoreRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: int
    vector_store_id: str | None = None


class CompanyVectorStoreCreatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None


class CompanyVectorStoreUpdatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vector_store_id: str | None = None


class CompanyVectorStoreFileRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    filename: str
    status: str
    usage_bytes: int
    created_at: datetime
    last_error_message: str | None = None


class CompanyVectorStoreFileBatchRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vector_store_id: str
    status: str
    uploaded_count: int
    completed_count: int
    failed_count: int
    cancelled_count: int
    in_progress_count: int


class CompanyBeelineIntegrationRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: int
    enabled: bool
    has_token: bool
    token_hint: str | None = None
    analysis_template_id: int | None = None
    last_sync_target_date: date | None = None
    last_sync_started_at: datetime | None = None
    last_sync_finished_at: datetime | None = None
    last_sync_status: str | None = None
    last_sync_error: str | None = None


class CompanyBeelineIntegrationUpdatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    api_token: str | None = None
    analysis_template_id: int | None = None


class CompanyBeelineIntegrationSyncRangePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date_from: date
    date_to: date
