from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.analyzer.schemas.criterion import Criterion
from src.analyzer.schemas.response import AnalyzerResponse
from src.database.schemas import CriterionRead
from src.enums import CriterionAnswerType, TranscriptionStatus
from src.app.services.auto_analysis import is_employee_detection_eligible


class FakeSessionManager:
    async def __aenter__(self):
        return SimpleNamespace(refresh=AsyncMock())

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
@pytest.mark.parametrize("existing_assignment", [None, 42])
@pytest.mark.parametrize("stale_report", [False, True])
@pytest.mark.parametrize("source_changes", [False, True])
async def test_auto_analyze_beeline_transcription_persists_detected_employee_user_id(monkeypatch, existing_assignment, stale_report, source_changes) -> None:
    from src.app.services import auto_analysis

    now = datetime.now(timezone.utc)
    transcription = SimpleNamespace(
        id=77,
        file_id="beeline_call_77",
        status=TranscriptionStatus.COMPLETED.value,
        text=(
            "Добрый день, компания Elixir. Меня зовут Иван Петров, я менеджер отдела продаж. "
            "Подскажите, пожалуйста, чем я могу вам помочь? Клиент подробно описывает вопрос по заказу."
        ),
        company_id=11,
        detected_employee_user_id=existing_assignment,
        transcribed_at=now,
    )
    company = SimpleNamespace(
        id=11,
        owner_id=5,
        vector_store_id=None,
        beeline_auto_analysis_template_id=19,
    )
    template = SimpleNamespace(
        id=19,
        company_id=11,
        name="База",
        instructions="Analyze carefully.",
    )
    criterion = CriterionRead(
        id=1,
        template_id=19,
        name="Greeting",
        description="Greeting quality",
        prompt="Check greeting quality",
        answer_type=CriterionAnswerType.TEXT,
        position=1,
        created_at=now,
        updated_at=now,
    )
    employee = SimpleNamespace(
        user_id=23,
        user=SimpleNamespace(name="Иван", surname="Петров", email="ivan@example.com"),
    )
    analyzer_response = AnalyzerResponse(
        summary="Call summary",
        employee_id=23,
        criteria_evaluated=[
            Criterion(
                id=1,
                answer_type=CriterionAnswerType.TEXT,
                answer="Хорошо",
                evidence=["Меня зовут Иван"],
            )
        ],
    )
    seen: dict[str, object] = {}

    def fake_get_session():
        return FakeSessionManager()

    async def fake_get_transcription_by_id(db, transcription_id):
        assert transcription_id == 77
        return transcription

    async def fake_get_company_by_id(db, company_id):
        assert company_id == 11
        return company

    async def fake_get_template_by_id(db, template_id):
        assert template_id == 19
        return template

    async def fake_get_analysis_by_transcription_id_and_template_id(db, transcription_id, template_id):
        from datetime import timedelta
        return SimpleNamespace(id=899, created_at=now - timedelta(hours=3)) if stale_report else None

    async def fake_list_criteria_by_template_id(db, template_id):
        assert template_id == 19
        return [criterion]

    async def fake_list_employees_by_company_id(db, company_id):
        assert company_id == 11
        return [employee]

    async def fake_analyze(*, request):
        seen["employee_options"] = request.employee_options
        if source_changes:
            transcription.text = "New transcript"
        return analyzer_response

    async def fake_create_analysis(db, payload, **kwargs):
        seen["analysis_summary"] = payload.summary
        seen["replaced_ids"] = kwargs.get("deactivate_analysis_ids")
        return SimpleNamespace(id=900)

    monkeypatch.setattr(auto_analysis, "get_session", fake_get_session)
    monkeypatch.setattr(auto_analysis, "get_transcription_by_id", fake_get_transcription_by_id)
    monkeypatch.setattr(auto_analysis, "get_company_by_id", fake_get_company_by_id)
    monkeypatch.setattr(auto_analysis, "get_template_by_id", fake_get_template_by_id)
    monkeypatch.setattr(auto_analysis, "get_analysis_by_transcription_id_and_template_id", fake_get_analysis_by_transcription_id_and_template_id)
    monkeypatch.setattr(auto_analysis, "list_criteria_by_template_id", fake_list_criteria_by_template_id)
    monkeypatch.setattr(auto_analysis, "list_employees_by_company_id", fake_list_employees_by_company_id)
    monkeypatch.setattr(auto_analysis.analyzer, "analyze", fake_analyze)
    monkeypatch.setattr(auto_analysis, "create_analysis", fake_create_analysis)

    result = await auto_analysis.auto_analyze_beeline_transcription(77)

    if source_changes:
        assert result is False
        assert "analysis_summary" not in seen
        assert transcription.detected_employee_user_id == existing_assignment
        return
    assert result is True
    assert seen["employee_options"] == {23: "Иван Петров"}
    if existing_assignment is None:
        assert transcription.detected_employee_user_id == 23
    else:
        assert transcription.detected_employee_user_id == existing_assignment
    assert seen["replaced_ids"] == ([899] if stale_report else None)
    assert seen["analysis_summary"] == "Call summary"


def test_employee_detection_rejects_transcription_hint_echo() -> None:
    company_hint = "Наша компания называется ElixirPeptide (ЭлисирПептайд)"
    names = ["Алия Ялалова", "Екатерина Колынбаева", "Елена Забродина", "Элина Гарипова"]
    transcript = (
        f"{company_hint}. Имена сотрудников для точного распознавания: "
        f"{', '.join(names)}."
    )

    assert not is_employee_detection_eligible(
        transcript,
        company_hint=company_hint,
        employee_names=names,
    )


def test_employee_detection_accepts_substantive_dialogue_with_employee_name() -> None:
    transcript = (
        "Добрый день, меня зовут Елена Забродина, компания ElixirPeptide. "
        "Клиент уточняет статус заказа и называет номер. Менеджер проверяет заказ, "
        "объясняет срок доставки, предлагает отправить трек-номер в Telegram и "
        "подтверждает, что посылка уже передана транспортной компании."
    )

    assert is_employee_detection_eligible(
        transcript,
        company_hint="Наша компания называется ElixirPeptide",
        employee_names=["Елена Забродина"],
    )
