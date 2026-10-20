from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from src.app.modules.transcriptions import router
from src.app.modules.transcriptions.schemas import TranscriptionListResponse, TranscriptionResponse
from src.database import get_db
from src.enums import TranscriptionStatus


@pytest.fixture
def client(monkeypatch):
    app = FastAPI()
    app.include_router(router.transcriptions_router)
    app.dependency_overrides[router.get_current_user] = lambda: SimpleNamespace(id=2)
    app.dependency_overrides[get_db] = lambda: object()
    monkeypatch.setattr(router, "get_accessible_company_or_404", AsyncMock(return_value=SimpleNamespace(id=1)))
    monkeypatch.setattr(router, "get_visible_user_ids_for_company", AsyncMock(return_value=[2]))
    monkeypatch.setattr(router, "list_transcription_summaries", AsyncMock(return_value=([], 0, 1)))
    with TestClient(app) as test_client:
        yield test_client


@pytest.mark.parametrize("query", [
    "page=0", "page_size=0", "page_size=101", "page_size=not-a-number",
    "employee=-2", "employee=invalid", "employee=0", "status=invalid",
])
def test_invalid_pagination_and_filters_are_rejected(client, query):
    response = client.get(f"/transcriptions/1/list/page?{query}")
    assert response.status_code == 422
    router.list_transcription_summaries.assert_not_awaited()


def test_scope_and_filters_are_forwarded(client):
    response = client.get(
        "/transcriptions/1/list/page?page=3&page_size=50&employee=2&status=completed&favorites_only=true"
    )
    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0, "page": 1, "page_size": 50}
    args, kwargs = router.list_transcription_summaries.await_args
    assert args[1:] == (1, 2)
    assert kwargs == dict(
        visible_user_ids=[2], page=3, page_size=50, employee="2",
        status=TranscriptionStatus.COMPLETED, favorites_only=True,
    )


def test_inaccessible_company_never_queries_list(client, monkeypatch):
    monkeypatch.setattr(router, "get_accessible_company_or_404", AsyncMock(side_effect=HTTPException(404)))
    assert client.get("/transcriptions/9/list/page").status_code == 404
    router.list_transcription_summaries.assert_not_awaited()


def test_summary_response_has_no_full_text_or_segments(client, monkeypatch):
    now = datetime(2026, 10, 20)
    row = dict(
        id=1, company_id=1, uploaded_by_user_id=2, uploaded_by_display_name="Employee",
        uploaded_by_email="user@example.test", detected_employee_user_id=None,
        detected_employee_display_name=None, detected_employee_email=None,
        file_id="file-1", original_filename="call.wav", status="completed", language="ru",
        text_preview="preview", has_text=True, error_message=None, is_favorite=True,
        call_started_at=None, transcribed_at=now, created_at=now, updated_at=now,
    )
    monkeypatch.setattr(router, "list_transcription_summaries", AsyncMock(return_value=([row], 1, 1)))
    data = client.get("/transcriptions/1/list/page").json()
    assert data["items"][0]["text_preview"] == "preview"
    assert data["items"][0]["media_url"]
    assert "text" not in data["items"][0]
    assert "segments" not in data["items"][0]


def test_legacy_list_and_detail_still_return_complete_transcripts(client, monkeypatch):
    now = datetime(2026, 10, 20)
    item = SimpleNamespace(id=1, status="completed")
    full = TranscriptionResponse(
        id=1, company_id=1, uploaded_by_user_id=2, file_id="file-1",
        original_filename="call.wav", status="completed", media_url="/media",
        text="complete transcript " * 1000, segments=[dict(start=0, end=1, text="full segment")],
        created_at=now, updated_at=now,
    )
    monkeypatch.setattr(router, "can_manage_company", lambda *args: True)
    monkeypatch.setattr(router, "list_transcriptions_by_company_id", AsyncMock(return_value=[item]))
    monkeypatch.setattr(router, "list_favorite_transcription_ids_for_user", AsyncMock(return_value=set()))
    monkeypatch.setattr(router, "get_accessible_transcription_by_file_or_404", AsyncMock(return_value=(item, True)))
    monkeypatch.setattr(router, "is_transcription_favorite", AsyncMock(return_value=False))
    monkeypatch.setattr(router, "build_transcription_response", lambda *args, **kwargs: full)
    legacy = client.get("/transcriptions/1")
    detail = client.get("/transcriptions/1/file-1")
    assert legacy.status_code == detail.status_code == 200
    assert legacy.json() == TranscriptionListResponse(items=[full]).model_dump(mode="json")
    assert detail.json() == full.model_dump(mode="json")
    router.list_transcription_summaries.assert_not_awaited()
