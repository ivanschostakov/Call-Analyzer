import uuid
import logging

from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from starlette.responses import FileResponse

from config import COMPANIES_UPLOAD_DIR, UPLOAD_MAX_BYTES
from src.app.observability import log_exception, log_info, log_state_change, log_warning
from src.app.modules.auth.dependencies import get_current_user
from src.app.modules.common import can_manage_company, get_accessible_company_or_404, get_visible_user_ids_for_company
from src.app.services.transcription_jobs import enqueue_transcription_job
from src.database import get_db
from src.database.crud import (
    create_transcription_favorite,
    create_transcription,
    delete_transcription_favorite,
    delete_transcription,
    is_transcription_favorite,
    list_transcriptions_by_company_id,
    list_transcriptions_by_company_id_and_visible_user_ids,
    list_favorite_transcription_ids_for_user,
)
from src.database.models import User
from src.database.schemas import TranscriptionCreate
from src.enums import TranscriptionStatus

from .helpers import build_upload_item_response, get_accessible_upload_or_404, is_supported_audio_upload, resolve_media_path, save_upload_file
from .schemas import UploadAudioResponse, UploadDeleteResponse, UploadItemResponse, UploadListResponse

uploads_router = APIRouter(prefix="/uploads", tags=["uploads"])
logger = logging.getLogger(__name__)

@uploads_router.get("/{company_id}", response_model=UploadListResponse)
async def list_uploads(company_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> UploadListResponse:
    log_info(logger, "uploads.list.start", actor_user_id=current_user.id, company_id=company_id)
    company = await get_accessible_company_or_404(db, current_user, company_id)
    if can_manage_company(current_user, company): items = await list_transcriptions_by_company_id(db, company_id)
    else:
        visible_user_ids = await get_visible_user_ids_for_company(db, current_user, company)
        if visible_user_ids is None: items = await list_transcriptions_by_company_id(db, company_id)
        else: items = await list_transcriptions_by_company_id_and_visible_user_ids(db, company_id, visible_user_ids)
    favorite_ids = await list_favorite_transcription_ids_for_user(db, current_user.id, [item.id for item in items])
    log_info(logger, "uploads.list.success", actor_user_id=current_user.id, company_id=company_id, count=len(items), favorite_count=len(favorite_ids))
    return UploadListResponse(items=[build_upload_item_response(item, is_favorite=item.id in favorite_ids) for item in items])


@uploads_router.get("/{company_id}/{file_id}", response_model=UploadItemResponse)
async def get_upload(company_id: int, file_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> UploadItemResponse:
    log_info(logger, "uploads.get.start", actor_user_id=current_user.id, company_id=company_id, file_id=file_id)
    transcription = await get_accessible_upload_or_404(db, current_user, company_id, file_id)
    favorite = await is_transcription_favorite(db, transcription.id, current_user.id)
    log_info(logger, "uploads.get.success", actor_user_id=current_user.id, company_id=company_id, file_id=file_id, transcription_id=transcription.id, is_favorite=favorite)
    return build_upload_item_response(transcription, is_favorite=favorite)


@uploads_router.get("/{company_id}/{file_id}/media")
async def get_upload_media(company_id: int, file_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> FileResponse:
    log_info(logger, "uploads.media.start", actor_user_id=current_user.id, company_id=company_id, file_id=file_id)
    transcription = await get_accessible_upload_or_404(db, current_user, company_id, file_id)
    media_path = resolve_media_path(transcription)
    if not media_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload file not found.")

    download_name = transcription.original_filename
    media_type = None
    if media_path == Path(transcription.file_path):
        original_stem = Path(transcription.original_filename).stem or transcription.file_id
        generated_suffix = media_path.suffix or ".wav"
        download_name = f"{original_stem}{generated_suffix}"
        media_type = mimetypes.guess_type(download_name)[0] or "application/octet-stream"

    log_info(
        logger,
        "uploads.media.success",
        actor_user_id=current_user.id,
        company_id=company_id,
        file_id=file_id,
        transcription_id=transcription.id,
        media_path=media_path,
        media_type=media_type,
    )
    return FileResponse(media_path, filename=download_name, media_type=media_type)


@uploads_router.post("/{company_id}", response_model=UploadAudioResponse, status_code=status.HTTP_201_CREATED)
async def upload_audio(company_id: int, file: UploadFile = File(...), current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> UploadAudioResponse:
    log_info(
        logger,
        "uploads.create.start",
        actor_user_id=current_user.id,
        company_id=company_id,
        filename=file.filename,
        content_type=file.content_type,
        max_upload_bytes=UPLOAD_MAX_BYTES,
    )
    await get_accessible_company_or_404(db, current_user, company_id)
    if not is_supported_audio_upload(file):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must be a supported audio format.",
        )

    company_dir = COMPANIES_UPLOAD_DIR / str(company_id)
    company_dir.mkdir(parents=True, exist_ok=True)

    file_id = uuid.uuid4().hex
    original_suffix = Path(file.filename or "").suffix or ".bin"
    safe_filename = Path(file.filename or "").name or f"{file_id}{original_suffix}"
    source_path = company_dir / f"{file_id}__source{original_suffix}"
    wav_path = company_dir / f"{file_id}.flac"
    transcription = None
    bytes_written = 0

    try:
        bytes_written = await save_upload_file(file, source_path)
        transcription = await create_transcription(
            db,
            TranscriptionCreate(
                company_id=company_id,
                uploaded_by_user_id=current_user.id,
                file_id=file_id,
                original_filename=safe_filename[:255],
                source_path=str(source_path),
                file_path=str(wav_path),
                status=TranscriptionStatus.QUEUED,
            ),
        )
        await enqueue_transcription_job(transcription.id)
        log_state_change(
            logger,
            "transcription",
            transcription.id,
            None,
            TranscriptionStatus.QUEUED.value,
            actor_user_id=current_user.id,
            company_id=company_id,
            file_id=file_id,
        )
    except HTTPException as exc:
        if transcription is not None:
            await delete_transcription(db, transcription)
        source_path.unlink(missing_ok=True)
        wav_path.unlink(missing_ok=True)
        log_warning(
            logger,
            "uploads.create.rejected",
            actor_user_id=current_user.id,
            company_id=company_id,
            filename=file.filename,
            source_path=source_path,
            wav_path=wav_path,
            status_code=exc.status_code,
            detail=exc.detail,
        )
        raise
    except Exception:
        if transcription is not None:
            await delete_transcription(db, transcription)
        source_path.unlink(missing_ok=True)
        wav_path.unlink(missing_ok=True)
        log_exception(
            logger,
            "uploads.create.failed",
            actor_user_id=current_user.id,
            company_id=company_id,
            filename=file.filename,
            source_path=source_path,
            wav_path=wav_path,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store uploaded audio.",
        )
    finally:
        await file.close()

    log_info(
        logger,
        "uploads.create.success",
        actor_user_id=current_user.id,
        company_id=company_id,
        transcription_id=transcription.id if transcription else None,
        file_id=file_id,
        filename=file.filename,
        bytes_written=bytes_written,
    )
    return UploadAudioResponse(**build_upload_item_response(transcription, is_favorite=False).model_dump())


@uploads_router.post("/{company_id}/{file_id}/favorite", response_model=UploadItemResponse, status_code=status.HTTP_200_OK)
async def favorite_upload(company_id: int, file_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> UploadItemResponse:
    log_info(logger, "uploads.favorite.start", actor_user_id=current_user.id, company_id=company_id, file_id=file_id)
    transcription = await get_accessible_upload_or_404(db, current_user, company_id, file_id)
    await create_transcription_favorite(db, transcription.id, current_user.id)
    log_info(logger, "uploads.favorite.success", actor_user_id=current_user.id, company_id=company_id, file_id=file_id, transcription_id=transcription.id)
    return build_upload_item_response(transcription, is_favorite=True)


@uploads_router.delete("/{company_id}/{file_id}/favorite", response_model=UploadItemResponse, status_code=status.HTTP_200_OK)
async def unfavorite_upload(company_id: int, file_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> UploadItemResponse:
    log_info(logger, "uploads.unfavorite.start", actor_user_id=current_user.id, company_id=company_id, file_id=file_id)
    transcription = await get_accessible_upload_or_404(db, current_user, company_id, file_id)
    await delete_transcription_favorite(db, transcription.id, current_user.id)
    log_info(logger, "uploads.unfavorite.success", actor_user_id=current_user.id, company_id=company_id, file_id=file_id, transcription_id=transcription.id)
    return build_upload_item_response(transcription, is_favorite=False)


@uploads_router.delete("/{company_id}/{file_id}", response_model=UploadDeleteResponse)
async def delete_upload(company_id: int, file_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> UploadDeleteResponse:
    log_info(logger, "uploads.delete.start", actor_user_id=current_user.id, company_id=company_id, file_id=file_id)
    transcription = await get_accessible_upload_or_404(db, current_user, company_id, file_id)

    Path(transcription.source_path).unlink(missing_ok=True)
    Path(transcription.file_path).unlink(missing_ok=True)
    await delete_transcription(db, transcription)

    log_info(logger, "uploads.delete.success", actor_user_id=current_user.id, company_id=company_id, file_id=file_id, transcription_id=transcription.id)
    return UploadDeleteResponse(ok=True, message="Upload deleted successfully.")
