import json
import logging

from .context import get_log_context
from .payloads import sanitize_mapping


class ContextAwareFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        context = sanitize_mapping(get_log_context())
        event_fields = sanitize_mapping(getattr(record, "event_fields", {}))
        combined = {**context, **event_fields}
        if not combined: return message

        rendered = " ".join(f"{key}={json.dumps(value, ensure_ascii=False, sort_keys=True)}" for key, value in sorted(combined.items()))
        return f"{message} {rendered}"
