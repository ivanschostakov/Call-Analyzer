import logging
import mimetypes
import time
import subprocess

from pathlib import Path
import aiofiles
from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from config import UPLOAD_MAX_BYTES
from src.app.observability import log_exception, log_info
from src.app.modules.common import (
    build_user_display_name,
    get_accessible_company_or_404,
    get_visible_user_ids_for_company,
    is_transcription_visible_to_user_ids,
)
from src.app.modules.uploads.schemas import UploadItemResponse
from src.database.crud import get_transcription_by_company_id_and_file_id
from src.database.models import Transcription, User
from src.enums import TranscriptionStatus

logger = logging.getLogger(__name__)
SUPPORTED_AUDIO_EXTENSIONS = {
    ".aac",
    ".flac",
    ".m4a",
    ".mp3",
    ".mp4",
    ".oga",
    ".ogg",
    ".wav",
    ".weba",
    ".webm",
    ".wma",
}
AMBIGUOUS_AUDIO_CONTENT_TYPES = {
    "",
    "application/octet-stream",
    "audio/mp4",
    "video/mp4",
}

def build_upload_item_response(transcription: Transcription, *, is_favorite: bool = False) -> UploadItemResponse:
    return UploadItemResponse(
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
        error_message=transcription.error_message,
        is_favorite=is_favorite,
        call_started_at=getattr(transcription, "call_started_at", None),
        created_at=transcription.created_at,
        updated_at=transcription.updated_at,
    )


async def get_accessible_upload_or_404(db: AsyncSession, current_user: User, company_id: int, file_id: str) -> Transcription:
    company = await get_accessible_company_or_404(db, current_user, company_id)
    transcription = await get_transcription_by_company_id_and_file_id(db, company_id, file_id)
    if transcription is None: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found.")
    visible_user_ids = await get_visible_user_ids_for_company(db, current_user, company)
    if is_transcription_visible_to_user_ids(transcription, visible_user_ids): return transcription
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found.")


def is_supported_audio_upload(upload: UploadFile) -> bool:
    content_type = (upload.content_type or "").split(";", 1)[0].strip().lower()
    if content_type.startswith("audio/"):
        return True

    suffix = Path(upload.filename or "").suffix.lower()
    if suffix in SUPPORTED_AUDIO_EXTENSIONS and content_type in AMBIGUOUS_AUDIO_CONTENT_TYPES:
        return True

    guessed_content_type, _ = mimetypes.guess_type(upload.filename or "")
    return bool(suffix in SUPPORTED_AUDIO_EXTENSIONS and (guessed_content_type or "").startswith("audio/"))


async def save_upload_file(upload: UploadFile, destination: Path, *, max_bytes: int = UPLOAD_MAX_BYTES) -> int:
    bytes_written = 0
    log_info(logger, "upload.file.save.start", filename=upload.filename, destination=destination, content_type=upload.content_type, max_bytes=max_bytes)
    async with aiofiles.open(destination, "wb") as buffer:
        while chunk := await upload.read(1024 * 1024):
            next_size = bytes_written + len(chunk)
            if next_size > max_bytes:
                raise HTTPException(
                    status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                    detail=f"Uploaded file exceeds the {max_bytes} byte limit.",
                )
            await buffer.write(chunk)
            bytes_written = next_size
    log_info(logger, "upload.file.save.success", filename=upload.filename, destination=destination, bytes_written=bytes_written)
    return bytes_written


def convert_to_wav(input_path: Path, output_path: Path) -> None:
    started_at = time.perf_counter()
    log_info(logger, "upload.audio.convert.start", input_path=input_path, output_path=output_path)
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(input_path),
                "-ac",
                "1",
                "-ar",
                "16000",
                "-vn",
                str(output_path),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
    except Exception:
        log_exception(logger, "upload.audio.convert.failed", input_path=input_path, output_path=output_path)
        raise
    log_info(
        logger,
        "upload.audio.convert.success",
        input_path=input_path,
        output_path=output_path,
        duration_ms=round((time.perf_counter() - started_at) * 1000, 3),
    )


def build_upload_media_url(company_id: int, file_id: str) -> str:
    return f"/uploads/{company_id}/{file_id}/media"


def resolve_media_path(transcription: Transcription) -> Path:
    wav_path = Path(transcription.file_path)
    if wav_path.exists():
        return wav_path
    return Path(transcription.source_path)


__all__ = [
    "build_upload_item_response",
    "get_accessible_upload_or_404",
    "save_upload_file",
    "convert_to_wav",
    "build_upload_media_url",
    "resolve_media_path",
]
