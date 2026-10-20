import pytest

from src.analyzer.request import AnalyzerRequest
from src.analyzer.schemas.response import AnalyzerResponse
from src.analyzer.schemas.criterion import Criterion
from src.analyzer.validation import validate_employee_evidence
from src.database.schemas import CriterionForAnalysis
from src.enums import CriterionAnswerType


def validate(quote, name, *, text=None, employee_id=7, options=None):
    request = AnalyzerRequest(
        call_transcription_text=text if text is not None else quote,
        criteria=[CriterionForAnalysis(id=1, name="Представился", description="Назвал ли имя?", prompt="Представился ли менеджер?", answer_type=CriterionAnswerType.BOOLEAN, position=0)],
        instructions="Check introduction",
        employee_options=options if options is not None else {6: "Елена Забродина", 7: "Элина Гарипова"},
    )
    response = AnalyzerResponse(
        summary="A call",
        employee_id=employee_id,
        employee_name=name,
        employee_introduction_quote=quote,
        criteria_evaluated=[Criterion(id=1, answer_type=CriterionAnswerType.BOOLEAN, answer=False, evidence=[])],
    )
    return validate_employee_evidence(request, response)


def test_report_1466_intro_is_positive_and_elena_not_elina():
    result = validate("Добрый день, компания Эликсир Пептид, менеджер Елены, я вас слушаю.", "Елена")
    assert result.employee_id == 6
    assert result.criteria_evaluated[0].answer is True
    assert "менеджер Елены" in result.criteria_evaluated[0].evidence[0]


def test_elina_is_not_elena():
    result = validate("Компания Эликсир, менеджер Элина, я вас слушаю.", "Элина", employee_id=6)
    assert result.employee_id == 7


def test_transcribed_case_ending_matches_without_changing_name():
    result = validate("Менеджер Елены, я вас слушаю.", "Елены")
    assert result.employee_id == 6


@pytest.mark.parametrize("name", ["Элина", "Елеина"])
def test_name_must_be_in_quote_without_invented_surname(name):
    result = validate("Менеджер Елена, я вас слушаю.", name)
    assert result.employee_id is None


def test_invented_surname_does_not_disambiguate_shared_first_name():
    result = validate("Менеджер Елена, я вас слушаю.", "Елена Забродина", options={6: "Елена Забродина", 8: "Елена Петрова"})
    assert result.employee_id is None
    assert result.employee_name == "елена"


def test_unspoken_surname_ignored_when_first_name_is_unique():
    result = validate("Менеджер Елены, я вас слушаю.", "Елена Забродина")
    assert result.employee_id == 6
    assert result.employee_name == "елена"


def test_fabricated_quote_is_not_accepted():
    result = validate("Менеджер Елена, я вас слушаю.", "Елена", text="Алло, добрый день.")
    assert result.employee_id is None
    assert result.criteria_evaluated[0].answer is False


def test_duplicate_first_names_remain_unassigned_but_intro_counts():
    result = validate("Менеджер Елена, я вас слушаю.", "Елена", options={6: "Елена Забродина", 8: "Елена Петрова"})
    assert result.employee_id is None
    assert result.criteria_evaluated[0].answer is True


def test_full_name_disambiguates():
    result = validate("Менеджер Елена Петрова, я вас слушаю.", "Елена Петрова", options={6: "Елена Забродина", 8: "Елена Петрова"})
    assert result.employee_id == 8


def test_unknown_employee_can_still_introduce_herself():
    result = validate("Менеджер Мария, я вас слушаю.", "Мария")
    assert result.employee_id is None
    assert result.criteria_evaluated[0].answer is True
