from enum import StrEnum


def enum_values(enum_cls: type[StrEnum]) -> list[str]:
    return [item.value for item in enum_cls]


class UserRole(StrEnum):
    OWNER = "owner"
    EMPLOYEE = "employee"
    ADMIN = "admin"


class TranscriptionStatus(StrEnum):
    UPLOADED = "uploaded"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class CriterionAnswerType(StrEnum):
    TEXT = "text"
    PERCENTAGE = "percentage"
    BOOLEAN = "boolean"
