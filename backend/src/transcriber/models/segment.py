from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class Segment:
    start: float
    end: float
    text: str

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Segment":
        return cls(
            start=round(float(payload.get("start", 0.0)), 3),
            end=round(float(payload.get("end", 0.0)), 3),
            text=str(payload.get("text", "")).strip(),
        )

    def to_dict(self) -> dict[str, float | str]:
        return {
            "start": self.start,
            "end": self.end,
            "text": self.text,
        }
