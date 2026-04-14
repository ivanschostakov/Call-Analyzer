from datetime import datetime, timezone
from types import SimpleNamespace

from src.app.modules.analysis.helpers import (
    build_report_summary_rows,
    resolve_report_summary_columns,
    serialize_report_summary_rows,
)
from src.database.schemas import CriterionRead
from src.enums import CriterionAnswerType


def build_criterion(criterion_id: int, name: str) -> CriterionRead:
    return CriterionRead(
        id=criterion_id,
        template_id=2,
        name=name,
        description="Criterion description",
        prompt="Criterion prompt",
        answer_type=CriterionAnswerType.BOOLEAN,
        position=0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def test_resolve_report_summary_columns_defaults_to_all_report_columns() -> None:
    criterion = build_criterion(17, "Greeting")

    columns = resolve_report_summary_columns([criterion], None)

    assert [column.key for column in columns] == [
        "callDate",
        "createdAt",
        "originalFilename",
        "templateName",
        "summary",
        "criterion-17",
    ]


def test_build_report_summary_rows_respects_selected_columns() -> None:
    criterion = build_criterion(17, "Greeting")
    selected_columns = resolve_report_summary_columns([criterion], ["summary", "criterion-17"])
    analysis = SimpleNamespace(
        id=101,
        created_at=datetime(2026, 3, 30, 12, 45, tzinfo=timezone.utc),
        template_name="Sales QA",
        summary="Менеджер уверенно провел разговор и хорошо отработал objections.",
        transcription=SimpleNamespace(original_filename="call-101.wav"),
        results=[
            SimpleNamespace(
                criterion_id=17,
                answer_type=CriterionAnswerType.BOOLEAN,
                answer=True,
            )
        ],
    )

    rows = build_report_summary_rows([analysis], selected_columns)
    serialized, omitted_row_count = serialize_report_summary_rows(selected_columns, rows, max_characters=10_000)

    assert rows[0].values["summary"].startswith("Менеджер уверенно")
    assert rows[0].values["criterion-17"] == "Да"
    assert "Сводка" in serialized
    assert "Greeting" in serialized
    assert "Дата анализа" not in serialized
    assert omitted_row_count == 0


def test_serialize_report_summary_rows_reports_omitted_rows_when_budget_is_small() -> None:
    criterion = build_criterion(17, "Greeting")
    selected_columns = resolve_report_summary_columns([criterion], ["summary"])
    rows = [
        SimpleNamespace(analysis_id=1, values={"summary": "A" * 90}),
        SimpleNamespace(analysis_id=2, values={"summary": "B" * 90}),
    ]

    serialized, omitted_row_count = serialize_report_summary_rows(selected_columns, rows, max_characters=120)

    assert "analysis_id=1" in serialized
    assert omitted_row_count == 1
