import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from src.analyzer.main import analyzer
from src.analyzer.request import AnalyzerRequest
from src.app.observability import log_exception, log_info
from src.app.modules.common import OperationResponse
from src.app.modules.analysis.helpers import (
    build_analysis_list_item_response,
    build_analysis_response,
    build_analysis_results,
    build_employee_detection_options,
    build_report_summary_rows,
    list_accessible_analyses_for_company,
    normalize_detected_employee_user_id,
    resolve_report_summary_columns,
    resolve_report_summary_template,
    resolve_analysis_template,
)
from src.app.modules.analysis.schemas import AnalysisCreatePayload, AnalysisRetryCriterionPayload, PerformanceChartPayload, PerformanceChartResponse, ReportSummaryCreatePayload, ReportSummaryResponse
from src.app.modules.auth.dependencies import get_current_user
from src.app.modules.common import (
    get_accessible_analysis_or_404,
    get_accessible_company_or_404,
    get_accessible_transcription_or_404,
    get_visible_user_ids_for_company,
    is_analysis_visible_to_user_ids,
)
from src.app.services.performance_chart import performance_chart_service
from src.app.services.report_summary import report_summary_service
from src.database import get_db
from src.database.crud import (
    create_analysis,
    deactivate_analysis,
    get_analysis_by_transcription_id_and_template_id,
    list_employees_by_company_id,
    list_analyses_by_ids,
    list_analyses_for_chart,
    list_criteria_by_template_id,
    update_transcription,
)
from src.database.models import User
from src.database.schemas import AnalysisCreate, AnalysisListItemRead, AnalysisRead, CriterionForAnalysis, CriterionRead, TranscriptionUpdate
from src.enums import TranscriptionStatus

analysis_router = APIRouter(prefix="/analysis", tags=["analysis"])
logger = logging.getLogger(__name__)


def build_analysis_request_criteria(
    criteria: list[CriterionRead] | None = None,
    override_payloads: list[AnalysisRetryCriterionPayload] | None = None,
) -> list[CriterionForAnalysis]:
    if override_payloads is not None:
        return [
            CriterionForAnalysis(
                id=item.criterion_id if item.criterion_id is not None else -(index + 1),
                name=item.name,
                description=item.description,
                prompt=item.prompt,
                answer_type=item.answer_type,
                position=item.position,
            )
            for index, item in enumerate(sorted(override_payloads, key=lambda criterion: criterion.position))
        ]

    return [
        CriterionForAnalysis(
            id=item.id,
            name=item.name,
            description=item.description,
            prompt=item.prompt,
            answer_type=item.answer_type,
            position=item.position,
        )
        for item in (criteria or [])
    ]

@analysis_router.get("", response_model=list[AnalysisListItemRead])
async def list_analysis_route(company_id: int = Query(...), current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> list[AnalysisListItemRead]:
    log_info(logger, "analysis.list.start", actor_user_id=current_user.id, company_id=company_id)
    items = await list_accessible_analyses_for_company(db, current_user, company_id)
    log_info(logger, "analysis.list.success", actor_user_id=current_user.id, company_id=company_id, count=len(items))
    return [build_analysis_list_item_response(item) for item in items]


@analysis_router.post("/report-summary", response_model=ReportSummaryResponse)
async def create_report_summary_route(
    payload: ReportSummaryCreatePayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReportSummaryResponse:
    log_info(
        logger,
        "analysis.report_summary.start",
        actor_user_id=current_user.id,
        company_id=payload.company_id,
        template_id=payload.template_id,
        analysis_count=len(payload.analysis_ids),
        selected_column_count=len(payload.columns or []),
        prompt_characters=len(payload.prompt.strip()),
    )
    company = await get_accessible_company_or_404(db, current_user, payload.company_id)
    template = await resolve_report_summary_template(db, current_user, payload.company_id, payload.template_id)
    visible_user_ids = await get_visible_user_ids_for_company(db, current_user, company)
    analyses = await list_analyses_by_ids(db, payload.analysis_ids)
    analysis_by_id = {analysis.id: analysis for analysis in analyses}
    missing_ids = [analysis_id for analysis_id in payload.analysis_ids if analysis_id not in analysis_by_id]
    if missing_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Some selected report rows were not found.")

    ordered_analyses = [analysis_by_id[analysis_id] for analysis_id in payload.analysis_ids]
    for analysis in ordered_analyses:
        if analysis.company_id != payload.company_id or analysis.template_id != payload.template_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="All selected rows must belong to the same report.")
        if not is_analysis_visible_to_user_ids(analysis, visible_user_ids):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Some selected report rows are not accessible.")

    criteria_models = await list_criteria_by_template_id(db, template.id)
    criteria = [CriterionRead.model_validate(item) for item in criteria_models]
    selected_columns = resolve_report_summary_columns(criteria, payload.columns)
    rows = build_report_summary_rows(ordered_analyses, selected_columns)
    if not rows:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="There are no selected report rows to summarize.")

    try:
        summary_result = await report_summary_service.summarize_report(
            template_name=template.name,
            question=payload.prompt,
            columns=selected_columns,
            rows=rows,
        )
    except HTTPException:
        raise
    except Exception as exc:
        log_exception(
            logger,
            "analysis.report_summary.failed",
            actor_user_id=current_user.id,
            company_id=payload.company_id,
            template_id=payload.template_id,
            detail=str(exc),
        )
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Report summarization failed: {exc}") from exc

    log_info(
        logger,
        "analysis.report_summary.success",
        actor_user_id=current_user.id,
        company_id=payload.company_id,
        template_id=payload.template_id,
        row_count=len(payload.analysis_ids),
        summarized_row_count=summary_result.summarized_row_count,
        omitted_row_count=summary_result.omitted_row_count,
    )
    return ReportSummaryResponse(
        company_id=payload.company_id,
        template_id=payload.template_id,
        analysis_ids=payload.analysis_ids,
        selected_columns=[column.key for column in selected_columns],
        selected_column_labels=[column.label for column in selected_columns],
        row_count=len(payload.analysis_ids),
        summarized_row_count=summary_result.summarized_row_count,
        omitted_row_count=summary_result.omitted_row_count,
        text=summary_result.text,
    )


@analysis_router.post("/performance-chart", response_model=PerformanceChartResponse)
async def create_performance_chart_route(
    payload: PerformanceChartPayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PerformanceChartResponse:
    log_info(
        logger,
        "analysis.performance_chart.start",
        actor_user_id=current_user.id,
        company_id=payload.company_id,
        template_id=payload.template_id,
        date_from=str(payload.date_from),
        date_to=str(payload.date_to),
        employee_user_id=payload.employee_user_id,
    )
    company = await get_accessible_company_or_404(db, current_user, payload.company_id)
    template = await resolve_report_summary_template(db, current_user, payload.company_id, payload.template_id)
    visible_user_ids = await get_visible_user_ids_for_company(db, current_user, company)

    analyses = await list_analyses_for_chart(
        db,
        company_id=payload.company_id,
        template_id=payload.template_id,
        date_from=payload.date_from,
        date_to=payload.date_to,
        employee_user_id=payload.employee_user_id,
        visible_user_ids=visible_user_ids,
    )

    try:
        result = await performance_chart_service.generate_chart(
            analyses=analyses,
            template_name=template.name,
        )
    except HTTPException:
        raise
    except Exception as exc:
        log_exception(
            logger,
            "analysis.performance_chart.failed",
            actor_user_id=current_user.id,
            company_id=payload.company_id,
            template_id=payload.template_id,
            detail=str(exc),
        )
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Performance chart generation failed: {exc}") from exc

    log_info(
        logger,
        "analysis.performance_chart.success",
        actor_user_id=current_user.id,
        company_id=payload.company_id,
        template_id=payload.template_id,
        analysis_count=len(analyses),
        day_count=len(result.calls),
    )
    return PerformanceChartResponse(
        company_id=payload.company_id,
        template_id=payload.template_id,
        calls=result.calls,
    )


@analysis_router.get("/{analysis_id}", response_model=AnalysisRead)
async def get_analysis_route(analysis_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> AnalysisRead:
    log_info(logger, "analysis.get.start", actor_user_id=current_user.id, analysis_id=analysis_id)
    analysis = await get_accessible_analysis_or_404(db, current_user, analysis_id)
    log_info(logger, "analysis.get.success", actor_user_id=current_user.id, analysis_id=analysis_id, company_id=analysis.company_id)
    return build_analysis_response(analysis)


@analysis_router.delete("/{analysis_id}", response_model=OperationResponse)
async def delete_analysis_route(analysis_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> OperationResponse:
    log_info(logger, "analysis.delete.start", actor_user_id=current_user.id, analysis_id=analysis_id)
    analysis = await get_accessible_analysis_or_404(db, current_user, analysis_id)
    await deactivate_analysis(db, analysis)
    log_info(logger, "analysis.delete.success", actor_user_id=current_user.id, analysis_id=analysis_id, company_id=analysis.company_id)
    return OperationResponse(message="Analysis hidden successfully.")


@analysis_router.post("", response_model=AnalysisRead, status_code=status.HTTP_201_CREATED)
async def create_analysis_route(
    payload: AnalysisCreatePayload,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnalysisRead:
    log_info(logger, "analysis.create.start", actor_user_id=current_user.id, payload=payload.model_dump())
    transcription = await get_accessible_transcription_or_404(db, current_user, payload.transcription_id)
    if transcription.status != TranscriptionStatus.COMPLETED.value or not transcription.text: raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only completed transcriptions with text can be analyzed.")

    template = await resolve_analysis_template(
        db,
        current_user,
        transcription.company_id,
        payload.template_id,
        require_instructions=payload.instructions is None,
    )
    existing_analysis = await get_analysis_by_transcription_id_and_template_id(db, transcription.id, template.id, only_active=True)
    if existing_analysis is not None and not payload.replace_existing:
        response.status_code = status.HTTP_200_OK
        log_info(
            logger,
            "analysis.create.skip_existing",
            actor_user_id=current_user.id,
            analysis_id=existing_analysis.id,
            transcription_id=transcription.id,
            template_id=template.id,
        )
        return build_analysis_response(existing_analysis)

    company = await get_accessible_company_or_404(db, current_user, template.company_id)
    criteria_models = await list_criteria_by_template_id(db, template.id)
    template_criteria = [CriterionRead.model_validate(item) for item in criteria_models]
    criteria = build_analysis_request_criteria(template_criteria, payload.criteria)
    if not criteria:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Template does not contain any criteria.")

    instructions = payload.instructions if payload.instructions is not None else template.instructions
    visible_user_ids = await get_visible_user_ids_for_company(db, current_user, company)
    employee_models = await list_employees_by_company_id(db, company.id)
    if visible_user_ids is not None:
        visible_user_ids_set = set(visible_user_ids)
        employee_models = [employee for employee in employee_models if employee.user_id in visible_user_ids_set]
    employee_options = build_employee_detection_options(employee_models)
    log_info(
        logger,
        "analysis.create.context",
        actor_user_id=current_user.id,
        transcription_id=transcription.id,
        company_id=company.id,
        template_id=template.id,
        criteria_count=len(criteria),
        employee_option_count=len(employee_options),
        vector_store_id=company.vector_store_id,
    )

    try:
        analyzer_response = await analyzer.analyze(
            request=AnalyzerRequest(
                call_transcription_text=transcription.text,
                criteria=criteria,
                instructions=instructions,
                employee_options=employee_options,
                vector_store_ids=[company.vector_store_id] if company.vector_store_id else None,
            )
        )
        analysis_results = build_analysis_results(criteria, analyzer_response)
        detected_employee_user_id = normalize_detected_employee_user_id(analyzer_response.employee_id, set(employee_options))
    except HTTPException:
        raise
    except ValidationError as exc:
        log_exception(logger, "analysis.create.invalid_payload", actor_user_id=current_user.id, transcription_id=transcription.id, template_id=template.id)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Analyzer returned invalid response format: {exc}") from exc
    except Exception as exc:
        log_exception(logger, "analysis.create.failed", actor_user_id=current_user.id, transcription_id=transcription.id, template_id=template.id, detail=str(exc))
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Analysis failed: {exc}") from exc

    existing_analysis = await get_analysis_by_transcription_id_and_template_id(db, transcription.id, template.id, only_active=True)
    if existing_analysis is not None and not payload.replace_existing:
        response.status_code = status.HTTP_200_OK
        log_info(
            logger,
            "analysis.create.skip_existing_after_generate",
            actor_user_id=current_user.id,
            analysis_id=existing_analysis.id,
            transcription_id=transcription.id,
            template_id=template.id,
        )
        return build_analysis_response(existing_analysis)

    if transcription.detected_employee_user_id != detected_employee_user_id:
        transcription = await update_transcription(
            db,
            transcription,
            TranscriptionUpdate(detected_employee_user_id=detected_employee_user_id),
        )

    try:
        active_analysis_to_replace = (
            await get_analysis_by_transcription_id_and_template_id(db, transcription.id, template.id, only_active=True)
            if payload.replace_existing
            else None
        )
        analysis = await create_analysis(
            db,
            AnalysisCreate(
                company_id=transcription.company_id,
                created_by_user_id=current_user.id,
                transcription_id=transcription.id,
                template_id=template.id,
                template_name=template.name,
                instructions=instructions or "",
                summary=analyzer_response.summary,
                criteria_evaluated=analysis_results,
            ),
            deactivate_analysis_ids=[active_analysis_to_replace.id] if active_analysis_to_replace is not None else None,
        )
    except IntegrityError:
        await db.rollback()
        existing_analysis = await get_analysis_by_transcription_id_and_template_id(db, transcription.id, template.id, only_active=True)
        if existing_analysis is None:
            raise
        response.status_code = status.HTTP_200_OK
        log_info(
            logger,
            "analysis.create.skip_existing_on_integrity_error",
            actor_user_id=current_user.id,
            analysis_id=existing_analysis.id,
            transcription_id=transcription.id,
            template_id=template.id,
        )
        return build_analysis_response(existing_analysis)

    log_info(
        logger,
        "analysis.create.success",
        actor_user_id=current_user.id,
        analysis_id=analysis.id,
        transcription_id=transcription.id,
        template_id=template.id,
        criteria_result_count=len(analysis_results),
        summary=analyzer_response.summary,
    )
    return build_analysis_response(analysis)
