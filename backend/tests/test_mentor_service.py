from types import SimpleNamespace

import pytest

from src.app.modules.analysis.helpers import ReportSummaryColumnDefinition, ReportSummaryRow
from src.app.services.mentor import MentorContext, MentorService


def build_context(rows: list[ReportSummaryRow] | None = None) -> MentorContext:
    return MentorContext(
        template_name="Продажи",
        user_prompt="Как я справляюсь?",
        columns=[ReportSummaryColumnDefinition(key="summary", label="Сводка", kind="base")],
        rows=rows or [ReportSummaryRow(analysis_id=101, values={"summary": "Менеджер уверенно провел звонок."})],
    )


class FakeConversations:
    def __init__(self) -> None:
        self.created: list[dict | None] = []

    async def create(self, metadata=None):
        self.created.append(metadata)
        return SimpleNamespace(id=f"conv-{len(self.created)}")


class FakeResponses:
    def __init__(self, *, fail_first: Exception | None = None) -> None:
        self.calls: list[dict] = []
        self.fail_first = fail_first

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.fail_first is not None and len(self.calls) == 1:
            raise self.fail_first
        conversation = kwargs["conversation"]
        conversation_id = conversation["id"] if isinstance(conversation, dict) else conversation.id
        return SimpleNamespace(
            output_text="Менторский ответ",
            output=[],
            conversation=SimpleNamespace(id=conversation_id),
        )


class FakeOpenAIClient:
    def __init__(self, *, fail_first: Exception | None = None) -> None:
        self.conversations = FakeConversations()
        self.responses = FakeResponses(fail_first=fail_first)


def build_service(fake_client: FakeOpenAIClient) -> MentorService:
    service = MentorService(openai_api_key=None, model_name="gpt-test")
    service._MentorService__client = fake_client
    return service


def test_build_user_prompt_includes_context_counts_and_selected_rows() -> None:
    rows = [ReportSummaryRow(analysis_id=101, values={"summary": "A"}), ReportSummaryRow(analysis_id=102, values={"summary": "B"})]
    prompt = MentorService.build_user_prompt(
        context=build_context(rows),
        rows_text="Строка 1\nСтрока 2",
        summarized_row_count=1,
        omitted_row_count=1,
    )

    assert "Шаблон отчета: Продажи" in prompt
    assert "Сообщение сотрудника: Как я справляюсь?" in prompt
    assert "Выбрано строк: 2" in prompt
    assert "Строк в контексте: 1" in prompt
    assert "В контекст не поместилось строк: 1." in prompt
    assert "Строка 1" in prompt


@pytest.mark.asyncio
async def test_send_message_creates_conversation_and_uses_file_search_tool() -> None:
    fake_client = FakeOpenAIClient()
    service = build_service(fake_client)

    result = await service.send_message(
        conversation_id=None,
        user_id=7,
        context=build_context(),
        vector_store_ids=["vs_company"],
    )

    assert result.text == "Менторский ответ"
    assert result.conversation_id == "conv-1"
    assert fake_client.conversations.created == [{"user_id": "7"}]
    assert fake_client.responses.calls[0]["conversation"]["id"] == "conv-1"
    assert fake_client.responses.calls[0]["tools"] == [{"type": "file_search", "vector_store_ids": ["vs_company"]}]
    assert "Данные выбранных звонков" in fake_client.responses.calls[0]["input"]


@pytest.mark.asyncio
async def test_send_message_retries_with_new_conversation_when_existing_conversation_is_invalid(monkeypatch) -> None:
    fake_client = FakeOpenAIClient(fail_first=RuntimeError("invalid conversation"))
    service = build_service(fake_client)
    monkeypatch.setattr(MentorService, "_should_retry_with_new_conversation", staticmethod(lambda exc: True))

    result = await service.send_message(
        conversation_id="conv-old",
        user_id=7,
        context=build_context(),
    )

    assert result.text == "Менторский ответ"
    assert result.conversation_id == "conv-1"
    assert result.conversation_reset_reason == "invalid_conversation"
    assert fake_client.responses.calls[0]["conversation"]["id"] == "conv-old"
    assert fake_client.responses.calls[1]["conversation"]["id"] == "conv-1"
