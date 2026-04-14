from contextvars import ContextVar, Token
from typing import Any


_log_context: ContextVar[dict[str, Any]] = ContextVar("log_context", default={})


def get_log_context() -> dict[str, Any]: return dict(_log_context.get())
def bind_log_context(**values: Any) -> Token:
    current = get_log_context()
    current.update({key: value for key, value in values.items() if value is not None})
    return _log_context.set(current)


def replace_log_context(**values: Any) -> Token: return _log_context.set({key: value for key, value in values.items() if value is not None})
def reset_log_context(token: Token) -> None: _log_context.reset(token)
