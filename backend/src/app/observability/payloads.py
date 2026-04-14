import json

from dataclasses import asdict, is_dataclass
from datetime import date, datetime, time
from enum import Enum
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import parse_qs

from pydantic import BaseModel


REDACTED = "[REDACTED]"
UNSTRUCTURED_TEXT_BODY = "[UNSTRUCTURED_TEXT_BODY_NOT_LOGGED]"
SENSITIVE_FIELD_TOKENS = {
    "password",
    "secret",
    "token",
    "authorization",
    "cookie",
    "api_key",
    "apikey",
    "smtp_password",
    "jwt_access_secret_key",
    "refresh_token",
    "access_token",
}


def is_sensitive_key(key: str | None) -> bool:
    if not key: return False
    normalized = key.lower().replace("-", "_")
    return any(token in normalized for token in SENSITIVE_FIELD_TOKENS)


def sanitize_for_logging(value: Any, *, field_name: str | None = None) -> Any:
    if is_sensitive_key(field_name):
        return REDACTED

    if value is None or isinstance(value, (bool, int, float)):
        return value

    if isinstance(value, str):
        return value

    if isinstance(value, bytes):
        return f"<{len(value)} bytes>"

    if isinstance(value, (datetime, date, time)):
        return value.isoformat()

    if isinstance(value, Path):
        return str(value)

    if isinstance(value, Enum):
        return value.value

    if isinstance(value, BaseModel):
        return sanitize_for_logging(value.model_dump(), field_name=field_name)

    if is_dataclass(value):
        return sanitize_for_logging(asdict(value), field_name=field_name)

    if isinstance(value, Mapping):
        return {
            str(key): sanitize_for_logging(item, field_name=str(key))
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple, set, frozenset)):
        return [sanitize_for_logging(item, field_name=field_name) for item in value]

    if hasattr(value, "to_dict") and callable(value.to_dict):
        return sanitize_for_logging(value.to_dict(), field_name=field_name)

    if hasattr(value, "__dict__"):
        public_items = {
            key: item
            for key, item in vars(value).items()
            if not key.startswith("_")
        }
        if public_items:
            return sanitize_for_logging(public_items, field_name=field_name)

    return str(value)


def sanitize_mapping(values: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: sanitize_for_logging(value, field_name=key)
        for key, value in values.items()
        if value is not None
    }


def sanitize_textual_payload(raw_text: str, *, content_type: str | None) -> Any:
    normalized = (content_type or "").split(";", 1)[0].strip().lower()
    if normalized == "application/json":
        try:
            parsed = json.loads(raw_text)
        except json.JSONDecodeError:
            return {
                "body_logged": False,
                "content_type": normalized,
                "reason": "invalid_json",
            }
        if isinstance(parsed, dict):
            return sanitize_for_logging(parsed, field_name="request_payload")
        if isinstance(parsed, list) and all(isinstance(item, (dict, list)) for item in parsed):
            return sanitize_for_logging(parsed, field_name="request_payload")
        if isinstance(parsed, list):
            return {
                "body_logged": False,
                "content_type": normalized,
                "reason": "scalar_json_array_body",
                "item_count": len(parsed),
            }
        return {
            "body_logged": False,
            "content_type": normalized,
            "reason": "scalar_json_body",
        }

    if normalized == "application/x-www-form-urlencoded":
        parsed = parse_qs(raw_text, keep_blank_values=True)
        return {
            key: sanitized_values[0] if len(sanitized_values) == 1 else sanitized_values
            for key, values in parsed.items()
            for sanitized_values in [sanitize_for_logging(values, field_name=key)]
        }

    return {
        "body_logged": False,
        "content_type": normalized or content_type,
        "reason": "unstructured_text",
        "body_preview": UNSTRUCTURED_TEXT_BODY,
    }
