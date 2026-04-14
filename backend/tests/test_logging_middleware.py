import logging

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.testclient import TestClient

from conftest import event_records
from src.app.observability import RequestLoggingMiddleware


def build_test_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    @app.post("/echo")
    async def echo(payload: dict) -> dict:
        return payload

    @app.post("/upload")
    async def upload(file: UploadFile = File(...)) -> dict:
        return {"filename": file.filename}

    @app.post("/text")
    async def text(request: Request) -> dict:
        return {"body": (await request.body()).decode("utf-8", errors="replace")}

    return app


def test_request_logging_emits_finish_and_sets_request_id(caplog) -> None:
    app = build_test_app()
    client = TestClient(app)
    caplog.set_level(logging.INFO)

    response = client.post("/echo?debug=1", json={"message": "hello", "password": "secret"})

    assert response.status_code == 200
    assert response.headers["x-request-id"]

    finish_record = event_records(caplog, "http.request.finish")[0]

    assert not event_records(caplog, "http.request.start")
    assert finish_record.event_fields["request_id"] == response.headers["x-request-id"]
    assert finish_record.event_fields["status_code"] == 200
    assert finish_record.event_fields["request_payload"]["message"] == "hello"
    assert finish_record.event_fields["request_payload"]["password"] == "[REDACTED]"


def test_request_logging_skips_binary_upload_bodies(caplog) -> None:
    app = build_test_app()
    client = TestClient(app)
    caplog.set_level(logging.INFO)

    response = client.post("/upload", files={"file": ("clip.wav", b"abc123", "audio/wav")})

    assert response.status_code == 200

    finish_record = event_records(caplog, "http.request.finish")[0]
    request_payload = finish_record.event_fields["request_payload"]

    assert request_payload["body_logged"] is False
    assert request_payload["body_bytes"] > 0
    assert "abc123" not in str(request_payload)


def test_request_logging_skips_unstructured_text_bodies(caplog) -> None:
    app = build_test_app()
    client = TestClient(app)
    caplog.set_level(logging.INFO)

    response = client.post("/text", content="refresh_token=secret-value", headers={"Content-Type": "text/plain"})

    assert response.status_code == 200

    finish_record = event_records(caplog, "http.request.finish")[0]
    request_payload = finish_record.event_fields["request_payload"]

    assert request_payload["body_logged"] is False
    assert request_payload["reason"] == "unstructured_text"
    assert "secret-value" not in str(request_payload)
