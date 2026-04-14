from datetime import datetime

from pydantic import BaseModel, ConfigDict

from src.enums import CriterionAnswerType


class CriterionBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    template_id: int
    name: str
    description: str | None = None
    prompt: str | None = None
    answer_type: CriterionAnswerType = CriterionAnswerType.TEXT
    position: int = 0


class CriterionForAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    name: str
    description: str | None = None
    prompt: str | None = None
    answer_type: CriterionAnswerType = CriterionAnswerType.TEXT
    position: int = 0


class CriterionCreate(CriterionBase):
    pass


class CriterionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    template_id: int | None = None
    name: str | None = None
    description: str | None = None
    prompt: str | None = None
    answer_type: CriterionAnswerType | None = None
    position: int | None = None


class CriterionRead(CriterionBase):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: int
    created_at: datetime
    updated_at: datetime
