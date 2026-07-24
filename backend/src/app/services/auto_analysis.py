import logging
import re

from pydantic import ValidationError

from src.analyzer.main import analyzer
from src.analyzer.request import AnalyzerRequest
from src.app.modules.analysis.helpers import build_analysis_results, build_employee_detection_options, normalize_detected_employee_user_id
from src.app.observability import log_exception, log_info, log_warning, start_timer
from src.database import get_session
from src.database.crud import (
    create_analysis,
    ensure_default_template_for_company,
    get_analysis_by_transcription_id_and_template_id,
    get_company_by_id,
    get_template_by_id,
    get_transcription_by_id,
    list_employees_by_company_id,
    list_criteria_by_template_id,
    update_transcription,
)
from src.database.schemas import AnalysisCreate, CriterionRead, TranscriptionUpdate
from src.enums import TranscriptionStatus

logger = logging.getLogger(__name__)
MIN_EMPLOYEE_DETECTION_TRANSCRIPT_CHARACTERS = 120


async def auto_analyze_beeline_transcription(transcription_id: int) -> bool:
    timer = start_timer()
    async with get_session() as db:
        transcription = await get_transcription_by_id(db, transcription_id)
        if transcription is None:
            log_warning(logger, "auto_analysis.beeline.skip_missing_transcription", transcription_id=transcription_id)
            return False
        if not transcription.file_id.startswith("beeline_"):
            log_info(logger, "auto_analysis.beeline.skip_non_beeline", transcription_id=transcription_id, file_id=transcription.file_id)
            return False
        if transcription.status != TranscriptionStatus.COMPLETED.value or not transcription.text:
            log_warning(logger, "auto_analysis.beeline.skip_incomplete", transcription_id=transcription_id, status=transcription.status)
            return False

        company = await get_company_by_id(db, transcription.company_id)
        if company is None:
            log_warning(logger, "auto_analysis.beeline.skip_missing_company", transcription_id=transcription_id, company_id=transcription.company_id)
            return False

        template = None
        if company.beeline_auto_analysis_template_id is not None:
            template = await get_template_by_id(db, company.beeline_auto_analysis_template_id)
            if template is not None and template.company_id != company.id:
                template = None
        if template is None:
            template = await ensure_default_template_for_company(db, company.id)
            await db.commit()
            await db.refresh(template)

        existing_analysis = await get_analysis_by_transcription_id_and_template_id(db, transcription.id, template.id)
        if existing_analysis is not None:
            log_info(
                logger,
                "auto_analysis.beeline.skip_existing",
                transcription_id=transcription_id,
                analysis_id=existing_analysis.id,
                template_id=template.id,
            )
            return False

        criteria_models = await list_criteria_by_template_id(db, template.id)
        if not criteria_models:
            log_warning(logger, "auto_analysis.beeline.skip_empty_template", transcription_id=transcription_id, template_id=template.id)
            return False

        criteria = [CriterionRead.model_validate(item) for item in criteria_models]
        employee_models = await list_employees_by_company_id(db, company.id)
        all_employee_options = build_employee_detection_options(employee_models)
        employee_options = all_employee_options if is_employee_detection_eligible(
            transcription.text,
            company_hint=getattr(company, "transcription_hint_prompt", None),
            employee_names=list(all_employee_options.values()),
        ) else {}
        company_vector_store_id = company.vector_store_id
        company_owner_id = company.owner_id
        transcription_company_id = transcription.company_id
        transcription_text = transcription.text

    log_info(
        logger,
        "auto_analysis.beeline.start",
        transcription_id=transcription_id,
        template_id=template.id,
        company_id=template.company_id,
        criteria_count=len(criteria),
        employee_option_count=len(employee_options),
    )

    try:
        analyzer_response = await analyzer.analyze(
            request=AnalyzerRequest(
                call_transcription_text=transcription_text,
                criteria=criteria,
                instructions=template.instructions,
                employee_options=employee_options,
                vector_store_ids=[company_vector_store_id] if company_vector_store_id else None,
            )
        )
        analysis_results = build_analysis_results(criteria, analyzer_response)
        detected_employee_user_id = normalize_detected_employee_user_id(analyzer_response.employee_id, set(employee_options))
    except ValidationError as exc:
        log_exception(logger, "auto_analysis.beeline.invalid_payload", transcription_id=transcription_id, template_id=template.id)
        raise RuntimeError(f"Analyzer returned invalid response format: {exc}") from exc
    except Exception as exc:
        log_exception(logger, "auto_analysis.beeline.failed", transcription_id=transcription_id, template_id=template.id, detail=str(exc))
        raise

    async with get_session() as db:
        transcription = await get_transcription_by_id(db, transcription_id)
        if transcription is None:
            log_warning(logger, "auto_analysis.beeline.skip_missing_transcription_after_generate", transcription_id=transcription_id)
            return False

        existing_analysis = await get_analysis_by_transcription_id_and_template_id(db, transcription_id, template.id)
        if existing_analysis is not None:
            log_info(
                logger,
                "auto_analysis.beeline.skip_existing_after_generate",
                transcription_id=transcription_id,
                analysis_id=existing_analysis.id,
                template_id=template.id,
            )
            return False

        if transcription.detected_employee_user_id != detected_employee_user_id:
            transcription = await update_transcription(
                db,
                transcription,
                TranscriptionUpdate(detected_employee_user_id=detected_employee_user_id),
            )

        analysis = await create_analysis(
            db,
            AnalysisCreate(
                company_id=transcription_company_id,
                created_by_user_id=company_owner_id,
                transcription_id=transcription_id,
                template_id=template.id,
                template_name=template.name,
                instructions=template.instructions,
                summary=analyzer_response.summary,
                criteria_evaluated=analysis_results,
            ),
        )

    log_info(
        logger,
        "auto_analysis.beeline.success",
        transcription_id=transcription_id,
        analysis_id=analysis.id,
        template_id=template.id,
        duration_ms=timer.elapsed_ms,
    )
    return True


def is_employee_detection_eligible(
    transcript_text: str,
    *,
    company_hint: str | None,
    employee_names: list[str],
) -> bool:
    normalized_text = transcript_text.casefold().strip()
    if len(normalized_text) < MIN_EMPLOYEE_DETECTION_TRANSCRIPT_CHARACTERS:
        return False

    content_without_hints = normalized_text
    removable_phrases = [
        company_hint or "",
        "имена сотрудников для точного распознавания",
        *employee_names,
    ]
    for phrase in removable_phrases:
        normalized_phrase = phrase.casefold().strip()
        if normalized_phrase:
            content_without_hints = content_without_hints.replace(normalized_phrase, " ")

    meaningful_characters = re.sub(r"[^a-zа-яё0-9]+", "", content_without_hints)
    return len(meaningful_characters) >= 80


__all__ = ["auto_analyze_beeline_transcription", "is_employee_detection_eligible"]
