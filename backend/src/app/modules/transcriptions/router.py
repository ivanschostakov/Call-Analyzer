from pathlib import Path
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from src.app.observability import log_info, log_state_change
from src.app.modules.auth.dependencies import get_current_user
from src.app.modules.common import (
    can_manage_company,
    forbidden_exception,
    get_accessible_company_or_404,
    get_visible_user_ids_for_company,
)
from src.app.services.transcription_jobs import enqueue_transcription_job
from src.database import get_db
from src.database.crud import (
    delete_transcription,
    get_employee_by_company_id_and_user_id,
    get_transcription_by_id,
    is_transcription_favorite,
    list_transcriptions_by_company_id,
    list_transcriptions_by_company_id_and_uploader_id,
    list_transcriptions_by_company_id_and_uploader_ids,
    list_favorite_transcription_ids_for_user,
    update_transcription,
)
from src.database.models import User
from src.database.schemas import TranscriptionUpdate
from src.enums import TranscriptionStatus

from .helpers import build_transcription_response, get_accessible_transcription_by_file_or_404
from .schemas import (
    TranscriptionDeleteResponse,
    TranscriptionEmployeeAssignment,
    TranscriptionListResponse,
    TranscriptionResponse,
)

transcriptions_router = APIRouter(prefix="/transcriptions", tags=["transcriptions"])
logger = logging.getLogger(__name__)


@transcriptions_router.get("/{company_id}", response_model=TranscriptionListResponse)
async def list_transcriptions(company_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> TranscriptionListResponse:
    log_info(logger, "transcriptions.list.start", actor_user_id=current_user.id, company_id=company_id)
    company = await get_accessible_company_or_404(db, current_user, company_id)
    if can_manage_company(current_user, company): items = await list_transcriptions_by_company_id(db, company_id)
    else:
        visible_user_ids = await get_visible_user_ids_for_company(db, current_user, company)
        if visible_user_ids is None: items = await list_transcriptions_by_company_id(db, company_id)
        elif len(visible_user_ids) == 1: items = await list_transcriptions_by_company_id_and_uploader_id(db, company_id, visible_user_ids[0])
        else: items = await list_transcriptions_by_company_id_and_uploader_ids(db, company_id, visible_user_ids)
    favorite_ids = await list_favorite_transcription_ids_for_user(db, current_user.id, [item.id for item in items])
    log_info(logger, "transcriptions.list.success", actor_user_id=current_user.id, company_id=company_id, count=len(items), favorite_count=len(favorite_ids))
    return TranscriptionListResponse(items=[build_transcription_response(item, is_favorite=item.id in favorite_ids) for item in items])


@transcriptions_router.get("/{company_id}/{file_id}", response_model=TranscriptionResponse)
async def get_transcription(company_id: int, file_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> TranscriptionResponse:
    log_info(logger, "transcriptions.get.start", actor_user_id=current_user.id, company_id=company_id, file_id=file_id)
    transcription, _ = await get_accessible_transcription_by_file_or_404(db, current_user, company_id, file_id)
    favorite = await is_transcription_favorite(db, transcription.id, current_user.id)
    log_info(logger, "transcriptions.get.success", actor_user_id=current_user.id, company_id=company_id, file_id=file_id, transcription_id=transcription.id, status=transcription.status, is_favorite=favorite)
    return build_transcription_response(transcription, is_favorite=favorite)


@transcriptions_router.post("/{company_id}/{file_id}", response_model=TranscriptionResponse, status_code=status.HTTP_202_ACCEPTED)
async def transcribe_upload(company_id: int, file_id: str, response: Response, force: bool = Query(default=False), current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> TranscriptionResponse:
    log_info(
        logger,
        "transcriptions.transcribe.start",
        actor_user_id=current_user.id,
        company_id=company_id,
        file_id=file_id,
        force=force,
    )
    transcription, _ = await get_accessible_transcription_by_file_or_404(db, current_user, company_id, file_id)
    favorite = await is_transcription_favorite(db, transcription.id, current_user.id)

    current_status = TranscriptionStatus(transcription.status)
    if current_status == TranscriptionStatus.COMPLETED and not force:
        response.status_code = status.HTTP_200_OK
        log_info(logger, "transcriptions.transcribe.skipped_completed", actor_user_id=current_user.id, transcription_id=transcription.id, status=current_status.value)
        return build_transcription_response(transcription, is_favorite=favorite)

    if current_status in {TranscriptionStatus.QUEUED, TranscriptionStatus.PROCESSING}:
        response.status_code = status.HTTP_202_ACCEPTED
        log_info(logger, "transcriptions.transcribe.skipped_active", actor_user_id=current_user.id, transcription_id=transcription.id, status=current_status.value)
        return build_transcription_response(transcription, is_favorite=favorite)

    transcription = await update_transcription(
        db,
        transcription,
        TranscriptionUpdate(
            status=TranscriptionStatus.QUEUED,
            language=None,
            text=None,
            segments=[],
            error_message=None,
            transcribed_at=None,
        ),
    )
    log_state_change(
        logger,
        "transcription",
        transcription.id,
        current_status.value,
        TranscriptionStatus.QUEUED.value,
        actor_user_id=current_user.id,
        company_id=company_id,
        file_id=file_id,
        force=force,
    )
    await enqueue_transcription_job(transcription.id)
    response.status_code = status.HTTP_202_ACCEPTED
    log_info(logger, "transcriptions.transcribe.queued", actor_user_id=current_user.id, transcription_id=transcription.id, status=transcription.status)
    return build_transcription_response(transcription, is_favorite=favorite)


@transcriptions_router.patch("/{company_id}/{file_id}/employee", response_model=TranscriptionResponse)
async def assign_transcription_employee(
    company_id: int,
    file_id: str,
    payload: TranscriptionEmployeeAssignment,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TranscriptionResponse:
    log_info(
        logger,
        "transcriptions.employee_assignment.start",
        actor_user_id=current_user.id,
        company_id=company_id,
        file_id=file_id,
        employee_user_id=payload.employee_user_id,
    )
    transcription, can_manage = await get_accessible_transcription_by_file_or_404(
        db,
        current_user,
        company_id,
        file_id,
    )
    if not can_manage:
        raise forbidden_exception("Only company administrators can assign calls to employees.")

    if payload.employee_user_id is not None:
        company = await get_accessible_company_or_404(db, current_user, company_id)
        membership = await get_employee_by_company_id_and_user_id(db, company_id, payload.employee_user_id)
        if membership is None and payload.employee_user_id != company.owner_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Selected user is not an employee of this company.",
            )

    previous_employee_user_id = transcription.detected_employee_user_id
    await update_transcription(
        db,
        transcription,
        TranscriptionUpdate(detected_employee_user_id=payload.employee_user_id),
    )
    refreshed = await get_transcription_by_id(db, transcription.id)
    if refreshed is None:
        raise RuntimeError("Updated transcription could not be reloaded.")

    favorite = await is_transcription_favorite(db, refreshed.id, current_user.id)
    log_state_change(
        logger,
        "transcription_employee_assignment",
        refreshed.id,
        previous_employee_user_id,
        payload.employee_user_id,
        actor_user_id=current_user.id,
        company_id=company_id,
        file_id=file_id,
    )
    return build_transcription_response(refreshed, is_favorite=favorite)


@transcriptions_router.delete("/{company_id}/{file_id}", response_model=TranscriptionDeleteResponse)
async def delete_transcription_route(company_id: int, file_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> TranscriptionDeleteResponse:
    log_info(logger, "transcriptions.delete.start", actor_user_id=current_user.id, company_id=company_id, file_id=file_id)
    transcription, _ = await get_accessible_transcription_by_file_or_404(db, current_user, company_id, file_id)

    source_path = Path(transcription.source_path)
    file_path = Path(transcription.file_path)
    source_path.unlink(missing_ok=True)
    file_path.unlink(missing_ok=True)
    await delete_transcription(db, transcription)
    log_info(logger, "transcriptions.delete.success", actor_user_id=current_user.id, company_id=company_id, file_id=file_id, transcription_id=transcription.id)
    return TranscriptionDeleteResponse(ok=True, message="Transcription deleted successfully.")
