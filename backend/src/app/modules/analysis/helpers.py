import logging
from dataclasses import dataclass
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from src.analyzer.schemas.response import AnalyzerResponse
from src.app.observability import log_warning
from src.app.modules.common import build_user_display_name, can_manage_company, get_accessible_company_or_404, get_accessible_template_or_404, get_visible_user_ids_for_company
from src.database.crud import list_analyses_by_company_id, list_analyses_by_company_id_and_creator_id, list_analyses_by_company_id_and_creator_ids
from src.database.models import Analysis, Employee, Template, User
from src.database.schemas import AnalysisListItemRead, AnalysisRead, AnalysisResultCreate, AnalysisResultRead, CriterionForAnalysis, CriterionRead
from src.enums import CriterionAnswerType

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ReportSummaryColumnDefinition:
    key: str
    label: str
    kind: str
    criterion_id: int | None = None


@dataclass(slots=True)
class ReportSummaryRow:
    analysis_id: int
    values: dict[str, str]


def format_report_summary_answer(answer_type: CriterionAnswerType, answer: str | int | bool | None) -> str:
    if answer_type == CriterionAnswerType.BOOLEAN:
        return "Да" if answer is True else "Нет"
    if answer_type == CriterionAnswerType.PERCENTAGE:
        return f"{answer}%" if isinstance(answer, int) and not isinstance(answer, bool) else "..."
    if answer is None:
        return "..."
    return str(answer).strip() or "..."


def format_report_summary_datetime(value: datetime) -> str:
    return value.strftime("%d.%m.%Y %H:%M")


def truncate_report_summary_value(value: str | None, *, max_length: int = 1200) -> str:
    normalized = (value or "").strip()
    if not normalized:
        return "..."
    if len(normalized) <= max_length:
        return normalized
    return f"{normalized[: max_length - 3].rstrip()}..."


def build_report_summary_columns(criteria: list[CriterionRead]) -> list[ReportSummaryColumnDefinition]:
    base_columns = [
        ReportSummaryColumnDefinition(key="callDate", label="Дата звонка", kind="base"),
        ReportSummaryColumnDefinition(key="createdAt", label="Дата анализа", kind="base"),
        ReportSummaryColumnDefinition(key="originalFilename", label="Звонок", kind="base"),
        ReportSummaryColumnDefinition(key="templateName", label="Шаблон", kind="base"),
        ReportSummaryColumnDefinition(key="summary", label="Сводка", kind="base"),
    ]
    criterion_columns = [
        ReportSummaryColumnDefinition(
            key=f"criterion-{criterion.id}",
            label=criterion.name,
            kind="criterion",
            criterion_id=criterion.id,
        )
        for criterion in sorted(criteria, key=lambda item: item.position)
    ]
    return [*base_columns, *criterion_columns]


def resolve_report_summary_columns(criteria: list[CriterionRead], requested_columns: list[str] | None) -> list[ReportSummaryColumnDefinition]:
    available_columns = build_report_summary_columns(criteria)
    if requested_columns is None:
        return available_columns
    if not requested_columns:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Select at least one report column for summarization.")

    columns_by_key = {column.key: column for column in available_columns}
    invalid_keys = [key for key in requested_columns if key not in columns_by_key]
    if invalid_keys:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown report columns: {', '.join(invalid_keys)}")
    return [columns_by_key[key] for key in requested_columns]


def build_report_summary_rows(analyses: list[Analysis], columns: list[ReportSummaryColumnDefinition]) -> list[ReportSummaryRow]:
    rows: list[ReportSummaryRow] = []
    for analysis in analyses:
        criterion_by_id = {
            item.criterion_id: item
            for item in analysis.results
            if item.criterion_id is not None
        }
        values: dict[str, str] = {}
        for column in columns:
            if column.kind == "base":
                if column.key == "callDate":
                    call_datetime = getattr(analysis.transcription, "call_started_at", None) if analysis.transcription else None
                    values[column.key] = format_report_summary_datetime(call_datetime or analysis.created_at)
                elif column.key == "createdAt":
                    values[column.key] = format_report_summary_datetime(analysis.created_at)
                elif column.key == "originalFilename":
                    values[column.key] = truncate_report_summary_value(
                        analysis.transcription.original_filename if analysis.transcription else "Без названия",
                        max_length=255,
                    )
                elif column.key == "templateName":
                    values[column.key] = truncate_report_summary_value(analysis.template_name, max_length=255)
                else:
                    values[column.key] = truncate_report_summary_value(analysis.summary, max_length=2000)
                continue

            criterion = criterion_by_id.get(column.criterion_id)
            values[column.key] = truncate_report_summary_value(
                format_report_summary_answer(criterion.answer_type, criterion.answer) if criterion else "...",
                max_length=600,
            )

        rows.append(ReportSummaryRow(analysis_id=analysis.id, values=values))
    return rows


def serialize_report_summary_rows(
    columns: list[ReportSummaryColumnDefinition],
    rows: list[ReportSummaryRow],
    *,
    max_characters: int = 120_000,
) -> tuple[str, int]:
    chunks: list[str] = []
    total_characters = 0
    omitted_row_count = 0

    for index, row in enumerate(rows, start=1):
        row_lines = [f"Строка {index} (analysis_id={row.analysis_id})"]
        row_lines.extend(f"- {column.label}: {row.values.get(column.key, '...')}" for column in columns)
        row_chunk = "\n".join(row_lines)
        prefix = "\n\n" if chunks else ""
        projected_total = total_characters + len(prefix) + len(row_chunk)
        if chunks and projected_total > max_characters:
            omitted_row_count = len(rows) - len(chunks)
            break
        if not chunks and len(row_chunk) > max_characters:
            chunks.append(row_chunk[:max_characters].rstrip())
            omitted_row_count = max(len(rows) - 1, 0)
            break

        chunks.append(row_chunk)
        total_characters = projected_total

    return "\n\n".join(chunks), omitted_row_count

def build_analysis_list_item_response(analysis) -> AnalysisListItemRead:
    return AnalysisListItemRead(
        id=analysis.id,
        company_id=analysis.company_id,
        created_by_user_id=analysis.created_by_user_id,
        created_by_display_name=build_user_display_name(analysis.created_by),
        created_by_email=analysis.created_by.email if analysis.created_by else None,
        transcription_id=analysis.transcription_id,
        template_id=analysis.template_id,
        template_name=analysis.template_name,
        summary=analysis.summary,
        is_active=analysis.is_active,
        created_at=analysis.created_at,
        updated_at=analysis.updated_at,
    )


def build_analysis_response(analysis) -> AnalysisRead:
    return AnalysisRead(
        id=analysis.id,
        company_id=analysis.company_id,
        created_by_user_id=analysis.created_by_user_id,
        created_by_display_name=build_user_display_name(analysis.created_by),
        created_by_email=analysis.created_by.email if analysis.created_by else None,
        transcription_id=analysis.transcription_id,
        template_id=analysis.template_id,
        template_name=analysis.template_name,
        instructions=analysis.instructions,
        summary=analysis.summary,
        is_active=analysis.is_active,
        criteria_evaluated=[AnalysisResultRead.model_validate(item) for item in analysis.criteria_evaluated],
        created_at=analysis.created_at,
        updated_at=analysis.updated_at,
    )


def build_employee_detection_options(employees: list[Employee]) -> dict[int, str]:
    options: dict[int, str] = {}
    for employee in employees:
        label = build_user_display_name(employee.user)
        if not label and employee.user is not None:
            label = employee.user.email
        if not label:
            label = f"Сотрудник #{employee.user_id}"
        options[employee.user_id] = label
    return options


def normalize_detected_employee_user_id(employee_user_id: int | None, valid_employee_user_ids: set[int]) -> int | None:
    if employee_user_id is None:
        return None
    if isinstance(employee_user_id, bool) or not isinstance(employee_user_id, int):
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Analyzer returned an invalid employee id.")
    if employee_user_id not in valid_employee_user_ids:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Analyzer returned an unknown employee id.")
    return employee_user_id

def normalize_percentage_answer(answer: str | int | float | bool) -> int:
    if not isinstance(answer, int) or isinstance(answer, bool):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Analyzer returned a non-numeric percentage answer.",
        )

    if not 0 <= answer <= 100:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Analyzer returned an out-of-range percentage answer.")
    return answer


def normalize_analysis_answer(expected_type: CriterionAnswerType, answer: str | int | float | bool) -> str | int | bool:
    if expected_type == CriterionAnswerType.BOOLEAN:
        if isinstance(answer, bool):
            return answer

        if isinstance(answer, str):
            normalized = answer.strip().lower()
            truthy_values = {"true", "yes", "da", "да", "1", "достигнута", "достигнуто", "выполнено", "есть"}
            falsy_values = {"false", "no", "net", "нет", "0", "не достигнута", "не достигнуто", "не выполнено", "нету"}
            if normalized in truthy_values:
                return True
            if normalized in falsy_values:
                return False

        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Analyzer returned an invalid boolean answer.")

    if expected_type == CriterionAnswerType.PERCENTAGE:
        return normalize_percentage_answer(answer)

    if isinstance(answer, str):
        return answer

    if expected_type == CriterionAnswerType.TEXT:
        if isinstance(answer, bool):
            return "Да" if answer else "Нет"
        return str(answer)

    raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Analyzer returned an invalid text answer.")


def build_analysis_results(criteria: list[CriterionForAnalysis], response: AnalyzerResponse) -> list[AnalysisResultCreate]:
    sorted_criteria = sorted(criteria, key=lambda item: item.position)
    returned_results = response.criteria_evaluated
    returned_ids = [item.id for item in returned_results]
    expected_ids = {criterion.id for criterion in sorted_criteria}
    has_unique_ids = len(set(returned_ids)) == len(returned_ids)
    can_match_by_id = has_unique_ids and set(returned_ids).issubset(expected_ids)

    if can_match_by_id:
        response_by_id = {item.id: item for item in returned_results}
        matched_items = [
            (criterion, result)
            for criterion in sorted_criteria
            if (result := response_by_id.get(criterion.id)) is not None
        ]
    else:
        if len(returned_results) != len(sorted_criteria):
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Analyzer returned an invalid criterion set.")

        log_warning(
            logger,
            "analysis.results.unexpected_criterion_ids",
            returned_ids=returned_ids,
            expected_ids=[criterion.id for criterion in sorted_criteria],
        )
        matched_items = list(zip(sorted_criteria, returned_results, strict=False))

    items: list[AnalysisResultCreate] = []
    for criterion, result in matched_items:
        normalized_answer = normalize_analysis_answer(criterion.answer_type, result.answer)
        if result.answer_type != criterion.answer_type:
            log_warning(
                logger,
                "analysis.results.answer_type_mismatch",
                returned_answer_type=result.answer_type,
                criterion_id=criterion.id,
                expected_answer_type=criterion.answer_type,
            )

        items.append(
            AnalysisResultCreate(
                criterion_id=criterion.id,
                criterion_name=criterion.name,
                criterion_description=criterion.description,
                criterion_prompt=criterion.prompt,
                answer_type=criterion.answer_type,
                answer=normalized_answer,
                evidence=result.evidence,
                position=criterion.position,
            )
        )

    if not items: raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Analyzer returned no persisted criterion results.")
    return items


async def resolve_analysis_template(
    db: AsyncSession,
    current_user: User,
    transcription_company_id: int,
    template_id: int,
    *,
    require_instructions: bool = True,
) -> Template:
    template = await get_accessible_template_or_404(db, current_user, template_id)
    if template.company_id != transcription_company_id: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Template must belong to the same company as the transcription.")
    if require_instructions and (not template.instructions or not template.instructions.strip()):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Template instructions must be set before analysis.")
    return template


async def resolve_report_summary_template(db: AsyncSession, current_user: User, company_id: int, template_id: int) -> Template:
    await get_accessible_company_or_404(db, current_user, company_id)
    template = await get_accessible_template_or_404(db, current_user, template_id)
    if template.company_id != company_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Template must belong to the selected company.")
    return template


async def list_accessible_analyses_for_company(db: AsyncSession, current_user: User, company_id: int) -> list[Analysis]:
    company = await get_accessible_company_or_404(db, current_user, company_id)
    if can_manage_company(current_user, company):
        return await list_analyses_by_company_id(db, company_id)

    visible_user_ids = await get_visible_user_ids_for_company(db, current_user, company)
    if visible_user_ids is None:
        return await list_analyses_by_company_id(db, company_id)
    if len(visible_user_ids) == 1:
        return await list_analyses_by_company_id_and_creator_id(db, company_id, visible_user_ids[0])
    return await list_analyses_by_company_id_and_creator_ids(db, company_id, visible_user_ids)
