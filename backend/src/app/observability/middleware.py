import logging
import uuid

from typing import Any

from config import LOG_HTTP_BODY_ENABLED, LOG_HTTP_BODY_MAX_BYTES

from .context import replace_log_context, reset_log_context
from .events import log_debug, log_info
from .payloads import sanitize_textual_payload


logger = logging.getLogger(__name__)
REQUEST_ID_HEADER = b"x-request-id"
OBSERVABILITY_STATE_KEY = "_observability"
TEXTUAL_CONTENT_TYPES = (
    "application/json",
    "application/x-www-form-urlencoded",
    "text/",
)


def get_observability_state(scope: dict[str, Any]) -> dict[str, Any]:
    state = scope.setdefault("state", {})
    observability_state = state.setdefault(OBSERVABILITY_STATE_KEY, {})
    return observability_state


def get_request_payload(scope: dict[str, Any]) -> Any: return get_observability_state(scope).get("request_payload")
def get_request_id(scope: dict[str, Any]) -> str | None: return get_observability_state(scope).get("request_id")
def is_textual_content_type(content_type: str | None) -> bool:
    if not content_type: return False
    normalized = content_type.lower()
    return normalized.startswith(TEXTUAL_CONTENT_TYPES)


class RequestLoggingMiddleware:
    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = {key.decode("latin1").lower(): value.decode("latin1") for key, value in scope.get("headers", [])}
        client = scope.get("client")
        request_id = headers.get("x-request-id") or uuid.uuid4().hex
        content_type = headers.get("content-type")
        content_length = headers.get("content-length")
        query_string = scope.get("query_string", b"").decode("utf-8", errors="replace")
        path = scope.get("path", "")
        method = scope.get("method", "UNKNOWN")
        client_ip = client[0] if client else None
        user_agent = headers.get("user-agent")
        should_capture_body = LOG_HTTP_BODY_ENABLED and is_textual_content_type(content_type)

        token = replace_log_context(
            request_id=request_id,
            http_method=method,
            http_path=path,
            http_query=query_string,
        )
        state = get_observability_state(scope)
        state.update(
            {
                "request_id": request_id,
                "content_type": content_type,
                "content_length": content_length,
                "query_string": query_string,
                "path": path,
                "method": method,
                "client_ip": client_ip,
                "user_agent": user_agent,
            }
        )

        body_parts: list[bytes] = []
        body_size = 0
        captured_body_size = 0
        body_capture_truncated = False
        response_status = 500
        response_started = False

        log_debug(
            logger,
            "http.request.start",
            request_id=request_id,
            method=method,
            path=path,
            query_string=query_string,
            client_ip=client_ip,
            user_agent=user_agent,
            content_type=content_type,
            content_length=content_length,
        )

        async def logging_receive():
            nonlocal body_size, captured_body_size, body_capture_truncated
            message = await receive()
            if message["type"] == "http.request":
                chunk = message.get("body", b"")
                body_size += len(chunk)
                if should_capture_body and chunk:
                    remaining_bytes = max(LOG_HTTP_BODY_MAX_BYTES - captured_body_size, 0)
                    if remaining_bytes > 0:
                        captured_chunk = chunk[:remaining_bytes]
                        body_parts.append(captured_chunk)
                        captured_body_size += len(captured_chunk)
                    if len(chunk) > remaining_bytes:
                        body_capture_truncated = True
                if not message.get("more_body", False):
                    if should_capture_body and not body_capture_truncated:
                        raw_text = b"".join(body_parts).decode("utf-8", errors="replace")
                        state["request_payload"] = sanitize_textual_payload(raw_text, content_type=content_type)
                    elif should_capture_body:
                        state["request_payload"] = {
                            "body_logged": False,
                            "body_bytes": body_size,
                            "captured_bytes": captured_body_size,
                            "content_type": content_type,
                            "reason": "body_too_large_for_logging",
                        }
                    else:
                        state["request_payload"] = {
                            "body_logged": False,
                            "body_bytes": body_size,
                            "content_type": content_type,
                        }
            return message

        async def logging_send(message):
            nonlocal response_status, response_started
            if message["type"] == "http.response.start":
                response_status = int(message["status"])
                response_started = True
                raw_headers = list(message.get("headers", []))
                raw_headers.append((REQUEST_ID_HEADER, request_id.encode("utf-8")))
                message["headers"] = raw_headers
            await send(message)

        from .events import start_timer

        timer = start_timer()
        try: await self.app(scope, logging_receive, logging_send)
        finally:
            request_payload = state.get("request_payload")
            log_info(
                logger,
                "http.request.finish",
                request_id=request_id,
                method=method,
                path=path,
                query_string=query_string,
                status_code=response_status,
                duration_ms=timer.elapsed_ms,
                client_ip=client_ip,
                user_agent=user_agent,
                content_type=content_type,
                content_length=content_length,
                body_bytes=body_size,
                request_payload=request_payload,
                response_started=response_started,
            )
            reset_log_context(token)
