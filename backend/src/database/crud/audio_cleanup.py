import logging
from datetime import datetime

from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.observability import log_info
from src.database.models import Transcription, TranscriptionFavorite
from src.enums import TranscriptionStatus

logger = logging.getLogger(__name__)


async def list_completed_transcriptions_for_wav_cleanup(
    db: AsyncSession,
) -> list[Transcription]:
    statement = select(Transcription).where(
        Transcription.status == TranscriptionStatus.COMPLETED.value,
    )
    items = list((await db.execute(statement)).scalars().all())
    log_info(logger, "crud.audio_cleanup.list_completed", count=len(items))
    return items


async def list_expired_unfavorited_transcriptions(
    db: AsyncSession,
    older_than: datetime,
) -> list[Transcription]:
    favorite_exists = exists(
        select(TranscriptionFavorite.id).where(
            TranscriptionFavorite.transcription_id == Transcription.id,
        )
    )
    statement = select(Transcription).where(
        func.coalesce(Transcription.call_started_at, Transcription.created_at) < older_than,
        Transcription.status.not_in(
            [
                TranscriptionStatus.QUEUED.value,
                TranscriptionStatus.PROCESSING.value,
            ]
        ),
        ~favorite_exists,
    )
    items = list((await db.execute(statement)).scalars().all())
    log_info(
        logger,
        "crud.audio_cleanup.list_expired_unfavorited",
        older_than=older_than.isoformat(),
        count=len(items),
    )
    return items
