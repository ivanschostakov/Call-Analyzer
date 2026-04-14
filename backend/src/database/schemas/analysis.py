from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, StrictStr, model_validator

from src.enums import CriterionAnswerType


class AnalysisResultBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    criterion_id: int | None = None
    criterion_name: str
    criterion_description: str | None = None
    criterion_prompt: str | None = None
    answer_type: CriterionAnswerType
    answer: StrictStr | StrictInt | StrictBool
    evidence: list[str] = Field(default_factory=list)
    position: int = 0

    @model_validator(mode="after")
    def validate_answer_shape(self) -> "AnalysisResultBase":
        if self.answer_type == CriterionAnswerType.BOOLEAN and not isinstance(self.answer, bool):
            raise ValueError("Boolean analysis results must use a boolean answer.")
        if self.answer_type == CriterionAnswerType.TEXT and not isinstance(self.answer, str):
            raise ValueError("Text analysis results must use a string answer.")
        if self.answer_type == CriterionAnswerType.PERCENTAGE:
            if not isinstance(self.answer, int) or isinstance(self.answer, bool):
                raise ValueError("Percentage analysis results must use an integer answer.")
            if not 0 <= self.answer <= 100:
                raise ValueError("Percentage analysis results must be between 0 and 100.")
        return self


class AnalysisResultCreate(AnalysisResultBase):
    pass


class AnalysisResultRead(AnalysisResultBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class AnalysisCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: int
    created_by_user_id: int | None = None
    transcription_id: int
    template_id: int
    template_name: str
    instructions: str
    summary: str
    criteria_evaluated: list[AnalysisResultCreate]


class AnalysisListItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    created_by_user_id: int | None
    created_by_display_name: str | None = None
    created_by_email: str | None = None
    transcription_id: int | None
    template_id: int | None
    template_name: str
    summary: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AnalysisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: int
    company_id: int
    created_by_user_id: int | None
    created_by_display_name: str | None = None
    created_by_email: str | None = None
    transcription_id: int | None
    template_id: int | None
    template_name: str
    instructions: str
    summary: str
    is_active: bool
    criteria_evaluated: list[AnalysisResultRead]
    created_at: datetime
    updated_at: datetime
