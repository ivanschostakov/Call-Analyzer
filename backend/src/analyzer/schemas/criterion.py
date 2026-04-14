from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, StrictStr, model_validator

from src.enums import CriterionAnswerType


class Criterion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    answer_type: CriterionAnswerType
    answer: StrictStr | StrictInt | StrictBool = Field(
        description="Text answers are strings, percentage answers are integers from 0 to 100, boolean answers are true/false."
    )
    evidence: list[str] = Field(default_factory=list, description="Short transcript-backed evidence items for this conclusion.")

    @model_validator(mode="after")
    def validate_answer_shape(self) -> "Criterion":
        if self.answer_type == CriterionAnswerType.BOOLEAN and not isinstance(self.answer, bool):
            raise ValueError("Boolean criteria must return a boolean answer.")
        if self.answer_type == CriterionAnswerType.TEXT and not isinstance(self.answer, str):
            raise ValueError("Text criteria must return a string answer.")
        if self.answer_type == CriterionAnswerType.PERCENTAGE:
            if not isinstance(self.answer, int) or isinstance(self.answer, bool):
                raise ValueError("Percentage criteria must return an integer answer.")
            if not 0 <= self.answer <= 100:
                raise ValueError("Percentage criteria must return a value from 0 to 100.")
        return self
