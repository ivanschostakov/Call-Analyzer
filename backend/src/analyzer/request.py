from dataclasses import dataclass

from src.database.schemas import CriterionForAnalysis


@dataclass
class AnalyzerRequest:
    call_transcription_text: str
    criteria: list[CriterionForAnalysis]
    instructions: str | None = None
    employee_options: dict[int, str] | None = None
    vector_store_ids: list[str] | None = None
