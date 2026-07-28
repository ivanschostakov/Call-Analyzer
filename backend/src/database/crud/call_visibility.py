import logging

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.app.observability import log_info
from src.database.models import Analysis, Transcription

logger = logging.getLogger(__name__)


def transcription_visibility_condition(visible_user_ids: list[int]):
    return or_(
        Transcription.detected_employee_user_id.in_(visible_user_ids),
        and_(
            Transcription.detected_employee_user_id.is_(None),
            Transcription.uploaded_by_user_id.in_(visible_user_ids),
        ),
    )


async def list_transcriptions_by_company_id_and_visible_user_ids(
    db: AsyncSession,
    company_id: int,
    visible_user_ids: list[int],
) -> list[Transcription]:
    statement = (
        select(Transcription)
        .options(
            selectinload(Transcription.uploaded_by),
            selectinload(Transcription.detected_employee_user),
        )
        .where(
            Transcription.company_id == company_id,
            transcription_visibility_condition(visible_user_ids),
        )
        .order_by(Transcription.updated_at.desc())
    )
    items = list((await db.execute(statement)).scalars().all())
    log_info(
        logger,
        "crud.transcriptions.list_by_company_and_visible_users",
        company_id=company_id,
        visible_user_ids=visible_user_ids,
        count=len(items),
    )
    return items


async def list_analyses_by_company_id_and_visible_user_ids(
    db: AsyncSession,
    company_id: int,
    visible_user_ids: list[int],
) -> list[Analysis]:
    statement = (
        select(Analysis)
        .outerjoin(Transcription, Analysis.transcription_id == Transcription.id)
        .options(
            selectinload(Analysis.created_by),
            selectinload(Analysis.transcription),
        )
        .where(
            Analysis.company_id == company_id,
            Analysis.is_active.is_(True),
            or_(
                and_(
                    Analysis.transcription_id.is_not(None),
                    transcription_visibility_condition(visible_user_ids),
                ),
                and_(
                    Analysis.transcription_id.is_(None),
                    Analysis.created_by_user_id.in_(visible_user_ids),
                ),
            ),
        )
        .order_by(Analysis.created_at.desc(), Analysis.id.desc())
    )
    items = list((await db.execute(statement)).scalars().all())
    log_info(
        logger,
        "crud.analyses.list_by_company_and_visible_users",
        company_id=company_id,
        visible_user_ids=visible_user_ids,
        count=len(items),
    )
    return items
