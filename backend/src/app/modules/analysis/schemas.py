from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.enums import CriterionAnswerType


class AnalysisRetryCriterionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    criterion_id: int | None = None
    name: str
    description: str | None = None
    prompt: str | None = None
    answer_type: CriterionAnswerType = CriterionAnswerType.TEXT
    position: int = 0


class AnalysisCreatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transcription_id: int
    template_id: int
    instructions: str | None = None
    replace_existing: bool = False
    criteria: list[AnalysisRetryCriterionPayload] | None = None


class ReportSummaryCreatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: int
    template_id: int
    analysis_ids: list[int] = Field(min_length=1)
    columns: list[str] | None = None
    prompt: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_prompt(self) -> "ReportSummaryCreatePayload":
        if not self.prompt.strip():
            raise ValueError("prompt must not be blank")
        return self


class ReportSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: int
    template_id: int
    analysis_ids: list[int]
    selected_columns: list[str]
    selected_column_labels: list[str]
    row_count: int
    summarized_row_count: int
    omitted_row_count: int
    text: str


class PerformanceCallData(BaseModel):
    call_count: int    # number of calls aggregated into this day
    label: str         # short display label shown on X-axis (formatted date)
    call_date: str     # ISO date string (YYYY-MM-DD) for this day
    overall_score: float


class PerformanceChartInternalResult(BaseModel):
    calls: list[PerformanceCallData]


class PerformanceChartPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: int
    template_id: int
    employee_user_id: int | None = None
    date_from: date
    date_to: date

    @model_validator(mode="after")
    def validate_date_range(self) -> "PerformanceChartPayload":
        if self.date_from > self.date_to:
            raise ValueError("date_from must not be after date_to")
        return self


class PerformanceChartResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: int
    template_id: int
    calls: list[PerformanceCallData]
