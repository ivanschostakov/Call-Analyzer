from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from fastapi import HTTPException

from src.app.modules.mentor.schemas import MentorMessageCreatePayload
from src.database.schemas import CriterionRead
from src.enums import CriterionAnswerType, UserRole


def build_user(user_id: int = 7):
    return SimpleNamespace(id=user_id, role=UserRole.EMPLOYEE)


def build_company():
    return SimpleNamespace(id=11, vector_store_id="vs_company")


def build_template():
    return SimpleNamespace(id=3, company_id=11, name="Продажи")


def build_criterion() -> CriterionRead:
    timestamp = datetime.now(timezone.utc)
    return CriterionRead(
        id=17,
        template_id=3,
        name="Приветствие",
        description=None,
        prompt=None,
        answer_type=CriterionAnswerType.BOOLEAN,
        position=0,
        created_at=timestamp,
        updated_at=timestamp,
    )


def build_analysis(*, created_by_user_id: int = 7):
    timestamp = datetime(2026, 4, 28, 12, 0, tzinfo=timezone.utc)
    return SimpleNamespace(
        id=101,
        company_id=11,
        template_id=3,
        created_by_user_id=created_by_user_id,
        created_at=timestamp,
        template_name="Продажи",
        summary="Менеджер уверенно провел звонок.",
        transcription=SimpleNamespace(
            original_filename="call.wav",
            call_started_at=timestamp,
            uploaded_by_user_id=created_by_user_id,
            detected_employee_user_id=None,
        ),
        results=[
            SimpleNamespace(
                criterion_id=17,
                answer_type=CriterionAnswerType.BOOLEAN,
                answer=True,
            )
        ],
    )


def build_thread(*, conversation_id: str | None = "conv-existing"):
    timestamp = datetime.now(timezone.utc)
    return SimpleNamespace(
        id=55,
        owner_user_id=7,
        company_id=11,
        template_id=3,
        openai_conversation_id=conversation_id,
        title="Existing thread",
        created_at=timestamp,
        updated_at=timestamp,
    )


class FakeMentorService:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def send_message(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            text="Вот разбор и следующие шаги.",
            conversation_id="conv-new",
            conversation_reset_reason=None,
            summarized_row_count=1,
            omitted_row_count=0,
        )


def test_build_thread_title_truncates_long_prompt() -> None:
    from src.app.modules.mentor.router import build_thread_title

    title = build_thread_title("a" * 120)

    assert len(title) == 80
    assert title.endswith("...")


@pytest.mark.asyncio
async def test_build_mentor_context_rejects_invisible_analysis(monkeypatch) -> None:
    from src.app.modules.mentor import router as mentor_router

    async def fake_get_accessible_company_or_404(db, current_user, company_id):
        return build_company()

    async def fake_resolve_report_summary_template(db, current_user, company_id, template_id):
        return build_template()

    async def fake_get_visible_user_ids_for_company(db, current_user, company):
        return [current_user.id]

    async def fake_list_analyses_by_ids(db, analysis_ids):
        return [build_analysis(created_by_user_id=99)]

    monkeypatch.setattr(mentor_router, "get_accessible_company_or_404", fake_get_accessible_company_or_404)
    monkeypatch.setattr(mentor_router, "resolve_report_summary_template", fake_resolve_report_summary_template)
    monkeypatch.setattr(mentor_router, "get_visible_user_ids_for_company", fake_get_visible_user_ids_for_company)
    monkeypatch.setattr(mentor_router, "list_analyses_by_ids", fake_list_analyses_by_ids)

    with pytest.raises(HTTPException) as exc:
        await mentor_router.build_mentor_context(
            db=None,
            current_user=build_user(),
            payload=MentorMessageCreatePayload(
                company_id=11,
                template_id=3,
                analysis_ids=[101],
                columns=["summary"],
                prompt="Помоги разобрать звонки",
            ),
        )

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_create_mentor_message_route_creates_new_thread_and_persists_messages(monkeypatch) -> None:
    from src.app.modules.mentor import router as mentor_router

    fake_service = FakeMentorService()
    created_messages = []

    async def fake_get_accessible_company_or_404(db, current_user, company_id):
        return build_company()

    async def fake_resolve_report_summary_template(db, current_user, company_id, template_id):
        return build_template()

    async def fake_get_visible_user_ids_for_company(db, current_user, company):
        return None

    async def fake_list_analyses_by_ids(db, analysis_ids):
        return [build_analysis()]

    async def fake_list_criteria_by_template_id(db, template_id):
        return [build_criterion()]

    async def fake_create_mentor_thread(db, payload):
        thread = build_thread(conversation_id=payload.openai_conversation_id)
        thread.title = payload.title
        return thread

    async def fake_create_mentor_message(db, payload):
        message = SimpleNamespace(
            id=len(created_messages) + 1,
            thread_id=payload.thread_id,
            role=payload.role,
            content=payload.content,
            analysis_ids=payload.analysis_ids,
            selected_columns=payload.selected_columns,
            row_count=payload.row_count,
            summarized_row_count=payload.summarized_row_count,
            omitted_row_count=payload.omitted_row_count,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        created_messages.append(message)
        return message

    monkeypatch.setattr(mentor_router, "mentor_service", fake_service)
    monkeypatch.setattr(mentor_router, "get_accessible_company_or_404", fake_get_accessible_company_or_404)
    monkeypatch.setattr(mentor_router, "resolve_report_summary_template", fake_resolve_report_summary_template)
    monkeypatch.setattr(mentor_router, "get_visible_user_ids_for_company", fake_get_visible_user_ids_for_company)
    monkeypatch.setattr(mentor_router, "list_analyses_by_ids", fake_list_analyses_by_ids)
    monkeypatch.setattr(mentor_router, "list_criteria_by_template_id", fake_list_criteria_by_template_id)
    monkeypatch.setattr(mentor_router, "create_mentor_thread", fake_create_mentor_thread)
    monkeypatch.setattr(mentor_router, "create_mentor_message", fake_create_mentor_message)

    response = await mentor_router.create_mentor_message_route(
        payload=MentorMessageCreatePayload(
            company_id=11,
            template_id=3,
            analysis_ids=[101],
            columns=["summary", "criterion-17"],
            prompt="Как я справляюсь?",
        ),
        current_user=build_user(),
        db=None,
    )

    assert response.thread.id == 55
    assert response.user_message.role == "user"
    assert response.assistant_message.role == "assistant"
    assert [message.role for message in created_messages] == ["user", "assistant"]
    assert fake_service.calls[0]["conversation_id"] is None
    assert fake_service.calls[0]["vector_store_ids"] == ["vs_company"]


@pytest.mark.asyncio
async def test_create_mentor_message_route_continues_existing_thread(monkeypatch) -> None:
    from src.app.modules.mentor import router as mentor_router

    fake_service = FakeMentorService()
    existing_thread = build_thread(conversation_id="conv-existing")
    created_thread_called = False

    async def fake_get_accessible_company_or_404(db, current_user, company_id):
        return build_company()

    async def fake_resolve_report_summary_template(db, current_user, company_id, template_id):
        return build_template()

    async def fake_get_visible_user_ids_for_company(db, current_user, company):
        return None

    async def fake_list_analyses_by_ids(db, analysis_ids):
        return [build_analysis()]

    async def fake_list_criteria_by_template_id(db, template_id):
        return [build_criterion()]

    async def fake_get_mentor_thread_by_id_and_owner_user_id(db, thread_id, owner_user_id):
        return existing_thread

    async def fake_update_mentor_thread(db, thread, payload):
        thread.openai_conversation_id = payload.openai_conversation_id
        thread.template_id = payload.template_id
        return thread

    async def fake_create_mentor_thread(db, payload):
        nonlocal created_thread_called
        created_thread_called = True
        return build_thread()

    async def fake_create_mentor_message(db, payload):
        return SimpleNamespace(
            id=1 if payload.role == "user" else 2,
            thread_id=payload.thread_id,
            role=payload.role,
            content=payload.content,
            analysis_ids=payload.analysis_ids,
            selected_columns=payload.selected_columns,
            row_count=payload.row_count,
            summarized_row_count=payload.summarized_row_count,
            omitted_row_count=payload.omitted_row_count,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    monkeypatch.setattr(mentor_router, "mentor_service", fake_service)
    monkeypatch.setattr(mentor_router, "get_accessible_company_or_404", fake_get_accessible_company_or_404)
    monkeypatch.setattr(mentor_router, "resolve_report_summary_template", fake_resolve_report_summary_template)
    monkeypatch.setattr(mentor_router, "get_visible_user_ids_for_company", fake_get_visible_user_ids_for_company)
    monkeypatch.setattr(mentor_router, "list_analyses_by_ids", fake_list_analyses_by_ids)
    monkeypatch.setattr(mentor_router, "list_criteria_by_template_id", fake_list_criteria_by_template_id)
    monkeypatch.setattr(mentor_router, "get_mentor_thread_by_id_and_owner_user_id", fake_get_mentor_thread_by_id_and_owner_user_id)
    monkeypatch.setattr(mentor_router, "update_mentor_thread", fake_update_mentor_thread)
    monkeypatch.setattr(mentor_router, "create_mentor_thread", fake_create_mentor_thread)
    monkeypatch.setattr(mentor_router, "create_mentor_message", fake_create_mentor_message)

    response = await mentor_router.create_mentor_message_route(
        payload=MentorMessageCreatePayload(
            thread_id=55,
            company_id=11,
            template_id=3,
            analysis_ids=[101],
            columns=["summary"],
            prompt="Продолжим",
        ),
        current_user=build_user(),
        db=None,
    )

    assert response.thread.id == 55
    assert created_thread_called is False
    assert fake_service.calls[0]["conversation_id"] == "conv-existing"
