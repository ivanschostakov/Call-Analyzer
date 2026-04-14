from __future__ import annotations

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
