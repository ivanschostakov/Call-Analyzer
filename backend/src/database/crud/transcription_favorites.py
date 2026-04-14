import logging as py_logging

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.observability import log_info
from src.database.models import TranscriptionFavorite

logger = py_logging.getLogger(__name__)


async def list_favorite_transcription_ids_for_user(
    db: AsyncSession,
    user_id: int,
    transcription_ids: list[int],
) -> set[int]:
    if not transcription_ids:
        return set()

    statement = select(TranscriptionFavorite.transcription_id).where(
        TranscriptionFavorite.user_id == user_id,
        TranscriptionFavorite.transcription_id.in_(transcription_ids),
    )
    rows = (await db.execute(statement)).scalars().all()
    favorites = {int(item) for item in rows}
    log_info(
        logger,
        "crud.transcription_favorites.list_for_user",
        user_id=user_id,
        transcription_count=len(transcription_ids),
        favorite_count=len(favorites),
    )
    return favorites


async def is_transcription_favorite(db: AsyncSession, transcription_id: int, user_id: int) -> bool:
    statement = select(TranscriptionFavorite.id).where(
        TranscriptionFavorite.transcription_id == transcription_id,
        TranscriptionFavorite.user_id == user_id,
    )
    favorite_id = (await db.execute(statement)).scalar_one_or_none()
    is_favorite = favorite_id is not None
    log_info(
        logger,
        "crud.transcription_favorites.exists",
        transcription_id=transcription_id,
        user_id=user_id,
        is_favorite=is_favorite,
    )
    return is_favorite


async def create_transcription_favorite(db: AsyncSession, transcription_id: int, user_id: int) -> TranscriptionFavorite:
    existing_statement = select(TranscriptionFavorite).where(
        TranscriptionFavorite.transcription_id == transcription_id,
        TranscriptionFavorite.user_id == user_id,
    )
    existing = (await db.execute(existing_statement)).scalar_one_or_none()
    if existing is not None:
        log_info(
            logger,
            "crud.transcription_favorites.create.skipped_existing",
            transcription_id=transcription_id,
            user_id=user_id,
        )
        return existing

    favorite = TranscriptionFavorite(transcription_id=transcription_id, user_id=user_id)
    db.add(favorite)
    await db.commit()
    await db.refresh(favorite)
    log_info(
        logger,
        "crud.transcription_favorites.create.success",
        favorite_id=favorite.id,
        transcription_id=transcription_id,
        user_id=user_id,
    )
    return favorite


async def delete_transcription_favorite(db: AsyncSession, transcription_id: int, user_id: int) -> bool:
    statement = delete(TranscriptionFavorite).where(
        TranscriptionFavorite.transcription_id == transcription_id,
        TranscriptionFavorite.user_id == user_id,
    )
    result = await db.execute(statement)
    await db.commit()
    deleted = bool(result.rowcount)
    log_info(
        logger,
        "crud.transcription_favorites.delete",
        transcription_id=transcription_id,
        user_id=user_id,
        deleted=deleted,
    )
    return deleted
