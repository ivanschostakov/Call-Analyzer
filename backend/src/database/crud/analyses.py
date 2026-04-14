import logging as py_logging

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.app.observability import log_info
from src.database.models import Analysis, AnalysisResult
from src.database.schemas import AnalysisCreate, AnalysisResultCreate
from src.enums import CriterionAnswerType

logger = py_logging.getLogger(__name__)


def _analysis_active_key(is_active: bool) -> int | None:
    return 1 if is_active else None


def _build_analysis_result(model: AnalysisResultCreate) -> AnalysisResult:
    answer_text = model.answer if model.answer_type == CriterionAnswerType.TEXT else None
    answer_number = model.answer if model.answer_type == CriterionAnswerType.PERCENTAGE else None
    answer_bool = model.answer if model.answer_type == CriterionAnswerType.BOOLEAN else None
    return AnalysisResult(
        criterion_id=model.criterion_id,
        criterion_name=model.criterion_name,
        criterion_description=model.criterion_description,
        criterion_prompt=model.criterion_prompt,
        answer_type=model.answer_type,
        answer_text=answer_text if isinstance(answer_text, str) else None,
        answer_number=answer_number if isinstance(answer_number, int) and not isinstance(answer_number, bool) else None,
        answer_bool=answer_bool if isinstance(answer_bool, bool) else None,
        evidence=list(model.evidence),
        position=model.position,
    )


async def deactivate_analysis(db: AsyncSession, analysis: Analysis) -> None:
    analysis.is_active = False
    analysis.active_key = _analysis_active_key(False)
    await db.commit()
    log_info(logger, "crud.analyses.deactivate", analysis_id=analysis.id, company_id=analysis.company_id)


async def create_analysis(db: AsyncSession, payload: AnalysisCreate, *, deactivate_analysis_ids: list[int] | None = None) -> Analysis:
    log_info(logger, "crud.analyses.create.start", payload=payload.model_dump())
    if deactivate_analysis_ids:
        await db.execute(
            update(Analysis)
            .where(Analysis.id.in_(deactivate_analysis_ids))
            .values(is_active=False, active_key=_analysis_active_key(False))
        )

    analysis = Analysis(
        company_id=payload.company_id,
        created_by_user_id=payload.created_by_user_id,
        transcription_id=payload.transcription_id,
        template_id=payload.template_id,
        template_name=payload.template_name,
        instructions=payload.instructions,
        summary=payload.summary,
        is_active=True,
        active_key=_analysis_active_key(True),
        results=[_build_analysis_result(item) for item in payload.criteria_evaluated],
    )
    db.add(analysis)
    await db.commit()
    saved_analysis = await get_analysis_by_id(db, analysis.id)
    if saved_analysis is None:
        raise RuntimeError("Created analysis could not be reloaded.")
    log_info(logger, "crud.analyses.create.success", analysis_id=saved_analysis.id, company_id=saved_analysis.company_id, result_count=len(saved_analysis.results))
    return saved_analysis


async def get_analysis_by_id(db: AsyncSession, analysis_id: int) -> Analysis | None:
    statement = (
        select(Analysis)
        .options(selectinload(Analysis.results), selectinload(Analysis.created_by))
        .where(Analysis.id == analysis_id)
    )
    analysis = (await db.execute(statement)).scalar_one_or_none()
    log_info(logger, "crud.analyses.get_by_id", analysis_id=analysis_id, found=bool(analysis))
    return analysis


async def get_analysis_by_transcription_id_and_template_id(
    db: AsyncSession,
    transcription_id: int,
    template_id: int,
    *,
    only_active: bool = True,
) -> Analysis | None:
    statement = (
        select(Analysis)
        .options(selectinload(Analysis.results), selectinload(Analysis.created_by))
        .where(
            Analysis.transcription_id == transcription_id,
            Analysis.template_id == template_id,
        )
        .order_by(Analysis.created_at.desc(), Analysis.id.desc())
        .limit(1)
    )
    if only_active:
        statement = statement.where(Analysis.is_active.is_(True))
    analysis = (await db.execute(statement)).scalar_one_or_none()
    log_info(
        logger,
        "crud.analyses.get_by_transcription_and_template",
        transcription_id=transcription_id,
        template_id=template_id,
        found=bool(analysis),
    )
    return analysis


async def list_analyses_by_company_id(db: AsyncSession, company_id: int) -> list[Analysis]:
    statement = (
        select(Analysis)
        .options(selectinload(Analysis.created_by))
        .where(Analysis.company_id == company_id, Analysis.is_active.is_(True))
        .order_by(Analysis.created_at.desc(), Analysis.id.desc())
    )
    items = list((await db.execute(statement)).scalars().all())
    log_info(logger, "crud.analyses.list_by_company", company_id=company_id, count=len(items))
    return items


async def list_analyses_by_company_id_and_creator_id(db: AsyncSession, company_id: int, created_by_user_id: int) -> list[Analysis]:
    statement = (
        select(Analysis)
        .options(selectinload(Analysis.created_by))
        .where(
            Analysis.company_id == company_id,
            Analysis.created_by_user_id == created_by_user_id,
            Analysis.is_active.is_(True),
        )
        .order_by(Analysis.created_at.desc(), Analysis.id.desc())
    )
    items = list((await db.execute(statement)).scalars().all())
    log_info(logger, "crud.analyses.list_by_company_and_creator", company_id=company_id, created_by_user_id=created_by_user_id, count=len(items))
    return items


async def list_analyses_by_company_id_and_creator_ids(db: AsyncSession, company_id: int, created_by_user_ids: list[int]) -> list[Analysis]:
    statement = (
        select(Analysis)
        .options(selectinload(Analysis.created_by))
        .where(
            Analysis.company_id == company_id,
            Analysis.created_by_user_id.in_(created_by_user_ids),
            Analysis.is_active.is_(True),
        )
        .order_by(Analysis.created_at.desc(), Analysis.id.desc())
    )
    items = list((await db.execute(statement)).scalars().all())
    log_info(logger, "crud.analyses.list_by_company_and_creators", company_id=company_id, created_by_user_ids=created_by_user_ids, count=len(items))
    return items


async def list_analyses_by_ids(db: AsyncSession, analysis_ids: list[int], *, only_active: bool = True) -> list[Analysis]:
    if not analysis_ids:
        return []

    statement = (
        select(Analysis)
        .options(
            selectinload(Analysis.results),
            selectinload(Analysis.transcription),
            selectinload(Analysis.created_by),
        )
        .where(Analysis.id.in_(analysis_ids))
    )
    if only_active:
        statement = statement.where(Analysis.is_active.is_(True))
    items = list((await db.execute(statement)).scalars().all())
    log_info(logger, "crud.analyses.list_by_ids", analysis_ids=analysis_ids, count=len(items))
    return items
