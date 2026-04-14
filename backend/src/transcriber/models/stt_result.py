from dataclasses import dataclass
from typing import Any

from .segment import Segment


@dataclass(slots=True)
class SttResult:
    text: str
    language: str
    segments: list[Segment]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SttResult":
        return cls(
            text=str(payload.get("text", "")).strip(),
            language=str(payload.get("language", "unknown")).strip() or "unknown",
            segments=[Segment.from_dict(item) for item in payload.get("segments", [])],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "language": self.language,
            "segments": [segment.to_dict() for segment in self.segments],
        }
