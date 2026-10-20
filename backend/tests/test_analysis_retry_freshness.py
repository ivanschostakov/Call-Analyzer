from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException, Response

from src.app.modules.analysis import router
from src.app.modules.analysis.schemas import AnalysisCreatePayload
from src.analyzer.schemas.response import AnalyzerResponse
from src.database.schemas import CriterionRead
from src.enums import CriterionAnswerType, UserRole


@pytest.mark.asyncio
@pytest.mark.parametrize("stale", [False, True])
@pytest.mark.parametrize("source_changes", [False, True])
async def test_existing_report_reused_only_for_current_transcript(monkeypatch, stale, source_changes):
    now = datetime.now(timezone.utc)
    transcription = SimpleNamespace(
        id=10, company_id=1, status="completed", text="Original text",
        transcribed_at=now, detected_employee_user_id=8,
    )
    old = SimpleNamespace(id=20, created_at=now + timedelta(hours=-1 if stale else 1))
    template = SimpleNamespace(id=3, company_id=1, name="Test", instructions="Check")
    company = SimpleNamespace(id=1, vector_store_id=None)
    criterion = CriterionRead(
        id=1, template_id=3, name="Greeting", description="", prompt="",
        answer_type=CriterionAnswerType.TEXT, position=0, created_at=now, updated_at=now,
    )
    model = AsyncMock(return_value=AnalyzerResponse(
        summary="New", employee_id=5,
        criteria_evaluated=[dict(id=1, answer_type="text", answer="Good", evidence=[])],
    ))
    create = AsyncMock(return_value=SimpleNamespace(id=21))
    for name, value in {
        "get_accessible_transcription_or_404": transcription,
        "resolve_analysis_template": template,
        "get_analysis_by_transcription_id_and_template_id": old,
        "get_accessible_company_or_404": company,
        "get_visible_user_ids_for_company": None,
        "list_criteria_by_template_id": [criterion],
        "list_employees_by_company_id": [],
    }.items():
        monkeypatch.setattr(router, name, AsyncMock(return_value=value))
    monkeypatch.setattr(router, "build_employee_detection_options", lambda _: {5: "Elena"})
    monkeypatch.setattr(router, "build_analysis_response", lambda item: item.id)
    monkeypatch.setattr(router.analyzer, "analyze", model)
    monkeypatch.setattr(router, "create_analysis", create)

    async def refresh(*args, **kwargs):
        if source_changes:
            transcription.text = "Changed while model was running"

    db = SimpleNamespace(refresh=refresh)
    payload = AnalysisCreatePayload(transcription_id=10, template_id=3)
    actor = SimpleNamespace(id=1, role=UserRole.ADMIN)
    if stale and source_changes:
        with pytest.raises(HTTPException) as error:
            await router.create_analysis_route(payload, Response(), actor, db)
        assert error.value.status_code == 409
        create.assert_not_awaited()
    else:
        result = await router.create_analysis_route(payload, Response(), actor, db)
        assert result == (21 if stale else 20)
        if stale:
            assert create.await_args.kwargs["deactivate_analysis_ids"] == [20]
            assert transcription.detected_employee_user_id == 8
        else:
            model.assert_not_awaited()
            create.assert_not_awaited()
