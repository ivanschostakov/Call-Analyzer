from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator


QueryScalar = str | int | float | bool | datetime | date
QueryValue = QueryScalar | Sequence[QueryScalar]


class BeelineModel(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True, str_strip_whitespace=True)


class BeelineAuthConfig(BeelineModel):
    token: str
    header_name: str = "X-MPBX-API-AUTH-TOKEN"
    header_scheme: str | None = None
    extra_headers: dict[str, str] = Field(default_factory=dict)

    def build_headers(self) -> dict[str, str]:
        headers = dict(self.extra_headers)
        value = self.token if not self.header_scheme else f"{self.header_scheme} {self.token}"
        headers[self.header_name] = value
        return headers


class BeelineSettings(BeelineModel):
    base_url: str
    timeout_seconds: float = 30.0
    auth: BeelineAuthConfig | None = None

    @classmethod
    def from_config(cls) -> "BeelineSettings":
        from config import BEELINE_API_BASE_URL, BEELINE_API_TIMEOUT_SECONDS

        return cls(
            base_url=BEELINE_API_BASE_URL,
            timeout_seconds=BEELINE_API_TIMEOUT_SECONDS,
        )


class BeelineCallRecord(BeelineModel):
    record_id: str | None = Field(default=None, validation_alias=AliasChoices("recordId", "record_id", "id"))
    ext_tracking_id: str | None = Field(default=None, validation_alias=AliasChoices("extTrackingId", "ext_tracking_id", "externalId"))
    user_id: str | None = Field(default=None, validation_alias=AliasChoices("userId", "user_id"))
    phone_number: str | None = Field(default=None, validation_alias=AliasChoices("phoneNumber", "phone_number", "phone"))
    external_number: str | None = Field(default=None, validation_alias=AliasChoices("externalNumber", "external_number"))
    started_at: datetime | None = Field(default=None, validation_alias=AliasChoices("startedAt", "startTime", "createdAt", "created_at"))
    ended_at: datetime | None = Field(default=None, validation_alias=AliasChoices("endedAt", "endTime", "updatedAt", "updated_at"))
    duration_seconds: int | None = Field(default=None, validation_alias=AliasChoices("durationSeconds", "duration", "duration_seconds"))
    status: str | None = None
    direction: str | None = None
    download_url: str | None = Field(default=None, validation_alias=AliasChoices("downloadUrl", "downloadURL"))
    reference_url: str | None = Field(default=None, validation_alias=AliasChoices("referenceUrl", "referenceURL", "reference"))

    @model_validator(mode="before")
    @classmethod
    def normalize_payload(cls, value: Any) -> Any:
        if not isinstance(value, Mapping):
            return value

        payload = dict(value)
        abonent = payload.get("abonent")
        if isinstance(abonent, Mapping):
            if payload.get("userId") is None and payload.get("user_id") is None:
                user_id = abonent.get("userId") or abonent.get("user_id")
                if user_id is not None:
                    payload["userId"] = user_id
            if payload.get("externalNumber") is None and payload.get("external_number") is None:
                abonent_phone = abonent.get("phone")
                if abonent_phone:
                    payload["externalNumber"] = abonent_phone

        if payload.get("startedAt") is None and payload.get("startTime") is None and payload.get("createdAt") is None:
            coerced_started_at = _coerce_beeline_datetime(payload.get("date"))
            if coerced_started_at is not None:
                payload["startedAt"] = coerced_started_at

        if payload.get("durationSeconds") is None and payload.get("duration_seconds") is None:
            coerced_duration = _coerce_beeline_duration_seconds(payload.get("duration"))
            if coerced_duration is not None:
                payload["durationSeconds"] = coerced_duration

        return payload


class BeelineRecordReference(BeelineModel):
    url: str | None = Field(default=None, validation_alias=AliasChoices("url", "reference", "referenceUrl", "referenceURL", "downloadUrl"))
    expires_at: datetime | None = Field(default=None, validation_alias=AliasChoices("expiresAt", "expires_at"))

    @classmethod
    def from_payload(cls, payload: Any) -> "BeelineRecordReference":
        if isinstance(payload, str):
            return cls(url=payload)
        return cls.model_validate(payload)


class BeelineDeleteResult(BeelineModel):
    ok: bool | None = Field(default=None, validation_alias=AliasChoices("ok", "success", "deleted"))
    message: str | None = None

    @classmethod
    def from_payload(cls, payload: Any) -> "BeelineDeleteResult":
        if payload is None:
            return cls(ok=True)
        if isinstance(payload, str):
            return cls(ok=True, message=payload)
        return cls.model_validate(payload)


@dataclass(slots=True)
class BeelineDownloadedFile:
    content: bytes
    content_type: str | None = None
    filename: str | None = None


def serialize_query_params(params: Mapping[str, QueryValue] | None) -> dict[str, str | list[str]]:
    if not params:
        return {}

    normalized: dict[str, str | list[str]] = {}
    for key, value in params.items():
        if value is None:
            continue
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            normalized_values = [_serialize_query_scalar(item) for item in value]
            if normalized_values:
                normalized[key] = normalized_values
            continue
        normalized[key] = _serialize_query_scalar(value)
    return normalized


def ensure_parent_dir(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _serialize_query_scalar(value: QueryScalar) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


def _coerce_beeline_datetime(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            numeric_value = float(value)
        except ValueError:
            return None
    elif isinstance(value, (int, float)):
        numeric_value = float(value)
    else:
        return None

    if abs(numeric_value) >= 10_000_000_000:
        numeric_value /= 1000.0

    return datetime.fromtimestamp(numeric_value, tz=timezone.utc)


def _coerce_beeline_duration_seconds(value: Any) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, str):
        try:
            numeric_value = float(value)
        except ValueError:
            return None
    elif isinstance(value, (int, float)):
        numeric_value = float(value)
    else:
        return None

    if numeric_value >= 1000:
        numeric_value /= 1000.0

    return max(int(round(numeric_value)), 0)
