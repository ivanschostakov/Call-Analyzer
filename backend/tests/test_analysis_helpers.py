import pytest

from fastapi import HTTPException
from pydantic import ValidationError
from types import SimpleNamespace

from src.app.modules.analysis.helpers import (
    build_employee_detection_options,
    format_report_summary_answer,
    normalize_analysis_answer,
    normalize_detected_employee_user_id,
)
from src.analyzer.schemas.criterion import Criterion
from src.enums import CriterionAnswerType


def test_normalize_analysis_answer_accepts_numeric_percentages_only() -> None:
    assert normalize_analysis_answer(CriterionAnswerType.PERCENTAGE, 73) == 73


def test_normalize_analysis_answer_rejects_string_percentage() -> None:
    with pytest.raises(HTTPException):
        normalize_analysis_answer(CriterionAnswerType.PERCENTAGE, "73%")


def test_normalize_analysis_answer_rejects_out_of_range_percentage() -> None:
    with pytest.raises(HTTPException):
        normalize_analysis_answer(CriterionAnswerType.PERCENTAGE, 120)


def test_format_report_summary_answer_formats_percentage_values() -> None:
    assert format_report_summary_answer(CriterionAnswerType.PERCENTAGE, 88) == "88%"


def test_analyzer_criterion_rejects_string_percentage_answer() -> None:
    with pytest.raises(ValidationError):
        Criterion(
            id=1,
            answer_type=CriterionAnswerType.PERCENTAGE,
            answer="88",
            evidence=[],
        )


def test_build_employee_detection_options_uses_employee_user_ids() -> None:
    options = build_employee_detection_options(
        [
            SimpleNamespace(
                user_id=17,
                user=SimpleNamespace(name="Иван", surname="Петров", email="ivan@example.com"),
            )
        ]
    )

    assert options == {17: "Иван Петров"}


def test_normalize_detected_employee_user_id_accepts_known_user_id() -> None:
    assert normalize_detected_employee_user_id(17, {17, 21}) == 17


def test_normalize_detected_employee_user_id_rejects_unknown_user_id() -> None:
    with pytest.raises(HTTPException):
        normalize_detected_employee_user_id(99, {17, 21})
