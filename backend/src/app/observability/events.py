import logging

from time import perf_counter
from typing import Any

from .payloads import sanitize_mapping


def log_event(logger: logging.Logger, level: int, event: str, /, **fields: Any) -> None: logger.log(level, event, extra={"event_fields": sanitize_mapping(fields)})
def log_debug(logger: logging.Logger, event: str, /, **fields: Any) -> None: log_event(logger, logging.DEBUG, event, **fields)
def log_info(logger: logging.Logger, event: str, /, **fields: Any) -> None: log_event(logger, logging.INFO, event, **fields)
def log_warning(logger: logging.Logger, event: str, /, **fields: Any) -> None: log_event(logger, logging.WARNING, event, **fields)
def log_error(logger: logging.Logger, event: str, /, **fields: Any) -> None: log_event(logger, logging.ERROR, event, **fields)
def log_exception(logger: logging.Logger, event: str, /, **fields: Any) -> None: logger.exception(event, extra={"event_fields": sanitize_mapping(fields)})
def log_state_change(logger: logging.Logger, entity: str, entity_id: Any, previous_state: Any, next_state: Any, /, **fields: Any) -> None: log_info(logger, f"{entity}.state_changed", entity_id=entity_id, previous_state=previous_state, next_state=next_state, **fields)


class LogTimer:
    def __init__(self) -> None: self._started_at = perf_counter()

    @property
    def elapsed_ms(self) -> float: return round((perf_counter() - self._started_at) * 1000, 3)


def start_timer() -> LogTimer: return LogTimer()
