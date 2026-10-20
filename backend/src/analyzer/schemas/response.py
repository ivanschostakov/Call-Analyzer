from pydantic import BaseModel, ConfigDict
from .criterion import Criterion


class AnalyzerResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str
    employee_id: int | None = None
    employee_name: str | None = None
    employee_introduction_quote: str | None = None
    criteria_evaluated: list[Criterion]
