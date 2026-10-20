from datetime import datetime
import logging as py_logging

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, selectinload

from config import ufa_now
from src.app.observability import log_info, log_state_change
from src.database.crud.call_visibility import transcription_visibility_condition
from src.database.models import Transcription, TranscriptionFavorite, User
from src.database.schemas import TranscriptionCreate, TranscriptionUpdate
from src.enums import TranscriptionStatus

logger = py_logging.getLogger(__name__)


async def list_transcription_summaries(
    db: AsyncSession,
    company_id: int,
    user_id: int,
    *,
    visible_user_ids: list[int] | None,
    page: int = 1,
    page_size: int = 25,
    employee: str = "all",
    status: TranscriptionStatus | None = None,
    favorites_only: bool = False,
) -> tuple[list[dict], int, int]:
    favorite = select(TranscriptionFavorite.id).where(
        TranscriptionFavorite.transcription_id == Transcription.id,
        TranscriptionFavorite.user_id == user_id,
    ).exists()
    conditions = [Transcription.company_id == company_id]
    if visible_user_ids is not None:
        conditions.append(transcription_visibility_condition(visible_user_ids))
    if employee == "unresolved":
        conditions.append(Transcription.detected_employee_user_id.is_(None))
    elif employee != "all":
        conditions.append(Transcription.detected_employee_user_id == int(employee))
    if status is not None:
        conditions.append(Transcription.status == status.value)
    if favorites_only:
        conditions.append(favorite)

    total = int(await db.scalar(select(func.count()).select_from(Transcription).where(*conditions)) or 0)
    page = min(page, max(1, (total + page_size - 1) // page_size))
    uploader = aliased(User)
    employee_user = aliased(User)

    def display_name(user):
        name = func.trim(func.coalesce(user.name, "") + " " + func.coalesce(user.surname, ""))
        return func.coalesce(func.nullif(name, ""), user.email)

    # Project bounded fields in SQL: never hydrate transcript text, segments or paths.
    statement = (
        select(
            Transcription.id, Transcription.company_id, Transcription.uploaded_by_user_id,
            display_name(uploader).label("uploaded_by_display_name"),
            uploader.email.label("uploaded_by_email"),
            Transcription.detected_employee_user_id,
            display_name(employee_user).label("detected_employee_display_name"),
            employee_user.email.label("detected_employee_email"),
            Transcription.file_id, Transcription.original_filename, Transcription.status,
            Transcription.language,
            func.substr(Transcription.text, 1, 180).label("text_preview"),
            (func.coalesce(Transcription.text, "") != "").label("has_text"),
            func.substr(Transcription.error_message, 1, 500).label("error_message"),
            favorite.label("is_favorite"),
            Transcription.call_started_at, Transcription.transcribed_at,
            Transcription.created_at, Transcription.updated_at,
        )
        .outerjoin(uploader, uploader.id == Transcription.uploaded_by_user_id)
        .outerjoin(employee_user, employee_user.id == Transcription.detected_employee_user_id)
        .where(*conditions)
        .order_by(func.coalesce(Transcription.call_started_at, Transcription.created_at).desc(), Transcription.id.desc())
        .limit(page_size)
        .offset((page - 1) * page_size)
    )
    rows = (await db.execute(statement)).mappings().all()
    return [dict(row) for row in rows], total, page


async def create_transcription(db: AsyncSession, payload: TranscriptionCreate) -> Transcription:
    log_info(logger, "crud.transcriptions.create.start", payload=payload.model_dump())
    data = payload.model_dump()
    data["segments"] = [segment.model_dump() if hasattr(segment, "model_dump") else dict(segment) for segment in data.get("segments", [])]

    transcription = Transcription(**data)
    db.add(transcription)
    await db.commit()
    await db.refresh(transcription)
    log_info(logger, "crud.transcriptions.create.success", transcription_id=transcription.id, company_id=transcription.company_id, status=transcription.status)
    return transcription


async def list_transcriptions_by_company_id(db: AsyncSession, company_id: int) -> list[Transcription]:
    statement = (
        select(Transcription)
        .options(selectinload(Transcription.uploaded_by), selectinload(Transcription.detected_employee_user))
        .where(Transcription.company_id == company_id)
        .order_by(Transcription.updated_at.desc())
    )
    items = list((await db.execute(statement)).scalars().all())
    log_info(logger, "crud.transcriptions.list_by_company", company_id=company_id, count=len(items))
    return items


async def list_transcriptions_by_company_id_and_uploader_id(db: AsyncSession, company_id: int, uploaded_by_user_id: int) -> list[Transcription]:
    statement = (
        select(Transcription)
        .options(selectinload(Transcription.uploaded_by), selectinload(Transcription.detected_employee_user))
        .where(
            Transcription.company_id == company_id,
            Transcription.uploaded_by_user_id == uploaded_by_user_id,
        )
        .order_by(Transcription.updated_at.desc())
    )
    items = list((await db.execute(statement)).scalars().all())
    log_info(logger, "crud.transcriptions.list_by_company_and_uploader", company_id=company_id, uploaded_by_user_id=uploaded_by_user_id, count=len(items))
    return items


async def list_transcriptions_by_company_id_and_uploader_ids(db: AsyncSession, company_id: int, uploaded_by_user_ids: list[int]) -> list[Transcription]:
    statement = (
        select(Transcription)
        .options(selectinload(Transcription.uploaded_by), selectinload(Transcription.detected_employee_user))
        .where(
            Transcription.company_id == company_id,
            Transcription.uploaded_by_user_id.in_(uploaded_by_user_ids),
        )
        .order_by(Transcription.updated_at.desc())
    )
    items = list((await db.execute(statement)).scalars().all())
    log_info(logger, "crud.transcriptions.list_by_company_and_uploaders", company_id=company_id, uploaded_by_user_ids=uploaded_by_user_ids, count=len(items))
    return items


async def get_transcription_by_company_id_and_file_id(db: AsyncSession, company_id: int, file_id: str) -> Transcription | None:
    statement = (
        select(Transcription)
        .options(selectinload(Transcription.uploaded_by), selectinload(Transcription.detected_employee_user))
        .where(Transcription.company_id == company_id, Transcription.file_id == file_id)
    )
    item = (await db.execute(statement)).scalar_one_or_none()
    log_info(logger, "crud.transcriptions.get_by_company_and_file", company_id=company_id, file_id=file_id, found=bool(item))
    return item


async def get_transcription_by_id(db: AsyncSession, transcription_id: int) -> Transcription | None:
    statement = (
        select(Transcription)
        .options(selectinload(Transcription.uploaded_by), selectinload(Transcription.detected_employee_user))
        .where(Transcription.id == transcription_id)
    )
    item = (await db.execute(statement)).scalar_one_or_none()
    log_info(logger, "crud.transcriptions.get_by_id", transcription_id=transcription_id, found=bool(item))
    return item


async def update_transcription(db: AsyncSession, transcription: Transcription, payload: TranscriptionUpdate) -> Transcription:
    previous_status = transcription.status
    updates = payload.model_dump(exclude_unset=True)
    if "segments" in updates and updates["segments"] is not None:
        updates["segments"] = [segment.model_dump() if hasattr(segment, "model_dump") else dict(segment) for segment in updates["segments"]]

    log_info(logger, "crud.transcriptions.update.start", transcription_id=transcription.id, changes=updates)
    for field, value in updates.items():
        setattr(transcription, field, value)

    db.add(transcription)
    await db.commit()
    await db.refresh(transcription)
    if previous_status != transcription.status:
        log_state_change(logger, "transcription", transcription.id, previous_status, transcription.status)
    log_info(logger, "crud.transcriptions.update.success", transcription_id=transcription.id, status=transcription.status)
    return transcription


async def delete_transcription(db: AsyncSession, transcription: Transcription) -> None:
    await db.delete(transcription)
    await db.commit()
    log_info(logger, "crud.transcriptions.delete", transcription_id=transcription.id, company_id=transcription.company_id)


async def delete_transcription_by_company_id_and_file_id(db: AsyncSession, company_id: int, file_id: str) -> None:
    statement = delete(Transcription).where(Transcription.company_id == company_id, Transcription.file_id == file_id)
    await db.execute(statement)
    await db.commit()
    log_info(logger, "crud.transcriptions.delete_by_company_and_file", company_id=company_id, file_id=file_id)


async def requeue_processing_transcriptions(db: AsyncSession, older_than: datetime | None = None) -> int:
    where_clause = [Transcription.status == TranscriptionStatus.PROCESSING.value]
    if older_than is not None:
        where_clause.append(Transcription.updated_at < older_than)
    statement = (
        update(Transcription)
        .where(*where_clause)
        .values(status=TranscriptionStatus.QUEUED.value, updated_at=ufa_now())
    )
    result = await db.execute(statement)
    await db.commit()
    recovered = int(result.rowcount or 0)
    if recovered:
        log_info(logger, "crud.transcriptions.requeue_processing", older_than=older_than.isoformat() if older_than else None, recovered=recovered)
    return recovered


async def claim_next_queued_transcription(db: AsyncSession) -> Transcription | None:
    candidate_statement = (
        select(Transcription)
        .where(Transcription.status == TranscriptionStatus.QUEUED.value)
        .order_by(Transcription.created_at.asc(), Transcription.id.asc())
        .limit(1)
    )
    candidate = (await db.execute(candidate_statement)).scalar_one_or_none()
    if candidate is None:
        log_info(logger, "crud.transcriptions.claim_next.empty")
        return None

    claim_statement = (
        update(Transcription)
        .where(
            Transcription.id == candidate.id,
            Transcription.status == TranscriptionStatus.QUEUED.value,
        )
        .values(status=TranscriptionStatus.PROCESSING.value, error_message=None, updated_at=ufa_now())
    )
    result = await db.execute(claim_statement)
    if not result.rowcount:
        candidate_id = candidate.id
        await db.rollback()
        log_info(logger, "crud.transcriptions.claim_next.raced", transcription_id=candidate_id)
        return None

    await db.commit()
    await db.refresh(candidate)
    log_state_change(logger, "transcription", candidate.id, TranscriptionStatus.QUEUED.value, TranscriptionStatus.PROCESSING.value)
    log_info(logger, "crud.transcriptions.claim_next.success", transcription_id=candidate.id)
    return candidate


async def touch_processing_transcription(db: AsyncSession, transcription_id: int) -> bool:
    statement = (
        update(Transcription)
        .where(
            Transcription.id == transcription_id,
            Transcription.status == TranscriptionStatus.PROCESSING.value,
        )
        .values(error_message=None, updated_at=ufa_now())
    )
    result = await db.execute(statement)
    await db.commit()
    touched = bool(result.rowcount)
    log_info(logger, "crud.transcriptions.touch_processing", transcription_id=transcription_id, touched=touched)
    return touched
