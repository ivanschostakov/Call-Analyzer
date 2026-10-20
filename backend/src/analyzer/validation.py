import re

from src.analyzer.request import AnalyzerRequest
from src.analyzer.schemas.response import AnalyzerResponse
from src.enums import CriterionAnswerType


def _words(value: str) -> list[str]:
    return re.findall(r"[a-zа-яё]+", value.casefold().replace("ё", "е"))


def _name_forms(name: str) -> set[str]:
    # Accept case endings, never edit-distance matches (Елена and Элина differ).
    forms = {name}
    if name.endswith("а"):
        forms.update(name[:-1] + ending for ending in ("ы", "е", "у", "ой"))
    elif name.endswith("я"):
        forms.update(name[:-1] + ending for ending in ("и", "е", "ю", "ей"))
    return forms


def validate_employee_evidence(request: AnalyzerRequest, result: AnalyzerResponse) -> AnalyzerResponse:
    quote = (result.employee_introduction_quote or "").strip()
    name_words = _words(result.employee_name or "")
    transcript = " ".join(request.call_transcription_text.casefold().split())
    normalized_quote = " ".join(quote.casefold().split())
    quote_words = set(_words(quote))
    explicit_introduction = bool(
        re.search(r"\b(?:меня зовут|менеджер|с вами)\b", normalized_quote)
    )
    grounded = (
        bool(quote and name_words)
        and explicit_introduction
        and normalized_quote in transcript
        and bool(_name_forms(name_words[0]) & quote_words)
    )
    if not grounded:
        return result.model_copy(update={"employee_id": None, "employee_introduction_quote": None, "employee_name": None})

    # Models may complete a first name with a roster surname absent from the call.
    # Only the spoken parts may disambiguate employees sharing a first name.
    name_words = [word for word in name_words if _name_forms(word) & quote_words]
    matching_ids = []
    for employee_id, label in (request.employee_options or {}).items():
        label_words = set(_words(label))
        if all(any(_name_forms(word) & _name_forms(label_word) for label_word in label_words) for word in name_words):
            matching_ids.append(employee_id)

    # The quote, not the model's preferred id, decides whether identity is unique.
    employee_id = matching_ids[0] if len(matching_ids) == 1 else None
    results = list(result.criteria_evaluated)
    criteria_by_id = {criterion.id: criterion for criterion in request.criteria}
    for index, item in enumerate(results):
        criterion = criteria_by_id.get(item.id)
        if (
            criterion is not None
            and criterion.name.strip().casefold() == "представился"
            and criterion.answer_type == CriterionAnswerType.BOOLEAN
            and explicit_introduction
        ):
            results[index] = item.model_copy(update={"answer": True, "evidence": [quote]})
    return result.model_copy(update={"employee_id": employee_id, "employee_name": " ".join(name_words), "criteria_evaluated": results})
