from pydantic import BaseModel, ConfigDict
from .criterion import Criterion


class AnalyzerResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str
    employee_id: int | None = None
    criteria_evaluated: list[Criterion]
