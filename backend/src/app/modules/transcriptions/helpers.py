from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from src.app.modules.common import build_user_display_name, can_manage_company, get_accessible_company_or_404, get_visible_user_ids_for_company
from src.app.modules.transcriptions.schemas import TranscriptionResponse
from src.app.modules.uploads.helpers import build_upload_media_url
from src.database.crud import get_transcription_by_company_id_and_file_id
from src.database.models import Transcription, User
from src.database.schemas import TranscriptionSegmentRead
from src.enums import TranscriptionStatus


def build_transcription_response(transcription: Transcription, *, is_favorite: bool = False) -> TranscriptionResponse:
    return TranscriptionResponse(
        id=transcription.id,
        company_id=transcription.company_id,
        uploaded_by_user_id=transcription.uploaded_by_user_id,
        uploaded_by_display_name=build_user_display_name(transcription.uploaded_by),
        uploaded_by_email=transcription.uploaded_by.email if transcription.uploaded_by else None,
        detected_employee_user_id=transcription.detected_employee_user_id,
        detected_employee_display_name=build_user_display_name(transcription.detected_employee_user),
        detected_employee_email=transcription.detected_employee_user.email if transcription.detected_employee_user else None,
        file_id=transcription.file_id,
        original_filename=transcription.original_filename,
        status=TranscriptionStatus(transcription.status),
        media_url=build_upload_media_url(transcription.company_id, transcription.file_id),
        language=transcription.language,
        text=transcription.text,
        segments=[TranscriptionSegmentRead.model_validate(item) for item in transcription.segments],
        error_message=transcription.error_message,
        is_favorite=is_favorite,
        call_started_at=getattr(transcription, "call_started_at", None),
        transcribed_at=transcription.transcribed_at,
        created_at=transcription.created_at,
        updated_at=transcription.updated_at,
    )


async def get_accessible_transcription_by_file_or_404(db: AsyncSession, current_user: User, company_id: int, file_id: str) -> tuple[Transcription, bool]:
    company = await get_accessible_company_or_404(db, current_user, company_id)
    transcription = await get_transcription_by_company_id_and_file_id(db, company_id, file_id)
    if transcription is None: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transcription not found.")

    visible_user_ids = await get_visible_user_ids_for_company(db, current_user, company)
    if visible_user_ids is None or transcription.uploaded_by_user_id in visible_user_ids: return transcription, can_manage_company(current_user, company)
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transcription not found.")


__all__ = [
    "build_transcription_response",
    "get_accessible_transcription_by_file_or_404",
]
