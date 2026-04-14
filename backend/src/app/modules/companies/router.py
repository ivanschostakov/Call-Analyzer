import logging

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from config import ufa_now
from .helpers import (
    build_company_beeline_integration_read,
    build_company_vector_store_file_batch_read,
    build_company_vector_store_file_read,
    build_company_vector_store_read,
    ensure_company_has_vector_store,
    raise_vector_store_http_error,
)
from ..auth.dependencies import get_current_user
from ..common import (
    OperationResponse,
    conflict_exception,
    ensure_can_create_company,
    get_accessible_company_or_404,
    get_manageable_company_or_404,
)
from .schemas import (
    CompanyBeelineIntegrationRead,
    CompanyBeelineIntegrationSyncRangePayload,
    CompanyBeelineIntegrationUpdatePayload,
    CompanyCreatePayload,
    CompanyUpdatePayload,
    CompanyVectorStoreCreatePayload,
    CompanyVectorStoreFileBatchRead,
    CompanyVectorStoreFileRead,
    CompanyVectorStoreRead,
    CompanyVectorStoreUpdatePayload,
)
from src.database import get_db
from src.database.crud import (
    create_company,
    delete_company,
    get_default_template_by_company_id,
    get_template_by_id,
    list_companies,
    list_companies_accessible_to_user_id,
    update_company,
)
from src.database.models import User
from src.database.schemas import CompanyCreate, CompanyRead, CompanyUpdate
from src.app.services.vector_store import vector_store_service
from src.app.observability import log_exception, log_info
from src.enums import UserRole

companies_router = APIRouter(prefix="/companies", tags=["companies"])
logger = logging.getLogger(__name__)

@companies_router.get("", response_model=list[CompanyRead])
async def list_companies_route(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> list[CompanyRead]:
    log_info(logger, "companies.list.start", actor_user_id=current_user.id)
    items = await list_companies(db) if current_user.role == UserRole.ADMIN else await list_companies_accessible_to_user_id(db, current_user.id)
    log_info(logger, "companies.list.success", actor_user_id=current_user.id, count=len(items))
    return [CompanyRead.model_validate(item) for item in items]


@companies_router.post("", response_model=CompanyRead, status_code=status.HTTP_201_CREATED)
async def create_company_route(payload: CompanyCreatePayload, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> CompanyRead:
    log_info(logger, "companies.create.start", actor_user_id=current_user.id, payload=payload.model_dump())
    await ensure_can_create_company(current_user)
    try:
        company = await create_company(
            db,
            CompanyCreate(
                owner_id=current_user.id,
                name=payload.name,
                description=payload.description,
            ),
        )
    except IntegrityError as exc:
        log_exception(logger, "companies.create.conflict", actor_user_id=current_user.id, name=payload.name)
        raise conflict_exception("Company with this name already exists.") from exc
    log_info(logger, "companies.create.success", actor_user_id=current_user.id, company_id=company.id, company_name=company.name)
    return CompanyRead.model_validate(company)


@companies_router.get("/{company_id}", response_model=CompanyRead)
async def get_company_route(company_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> CompanyRead:
    log_info(logger, "companies.get.start", actor_user_id=current_user.id, company_id=company_id)
    company = await get_accessible_company_or_404(db, current_user, company_id)
    log_info(logger, "companies.get.success", actor_user_id=current_user.id, company_id=company.id)
    return CompanyRead.model_validate(company)


@companies_router.get("/{company_id}/integrations/beeline", response_model=CompanyBeelineIntegrationRead)
async def get_company_beeline_integration_route(company_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> CompanyBeelineIntegrationRead:
    log_info(logger, "companies.integrations.beeline.get.start", actor_user_id=current_user.id, company_id=company_id)
    company = await get_manageable_company_or_404(db, current_user, company_id)
    log_info(
        logger,
        "companies.integrations.beeline.get.success",
        actor_user_id=current_user.id,
        company_id=company.id,
        enabled=company.beeline_auto_export_enabled,
        has_token=bool((company.beeline_api_token or "").strip()),
        last_sync_status=company.beeline_last_sync_status,
    )
    return build_company_beeline_integration_read(company)


@companies_router.put("/{company_id}/integrations/beeline", response_model=CompanyBeelineIntegrationRead)
async def set_company_beeline_integration_route(
    company_id: int,
    payload: CompanyBeelineIntegrationUpdatePayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CompanyBeelineIntegrationRead:
    log_info(logger, "companies.integrations.beeline.set.start", actor_user_id=current_user.id, company_id=company_id, payload=payload.model_dump())
    company = await get_manageable_company_or_404(db, current_user, company_id)
    should_run_immediate_sync = (not company.beeline_auto_export_enabled) or (payload.api_token is not None)
    token = payload.api_token or company.beeline_api_token
    if not token or not token.strip():
        raise conflict_exception("Provide a Beeline token to enable the integration.")

    selected_template_id = payload.analysis_template_id
    if selected_template_id is None:
        selected_template_id = company.beeline_auto_analysis_template_id
    if selected_template_id is None:
        default_template = await get_default_template_by_company_id(db, company.id)
        selected_template_id = default_template.id if default_template is not None else None
    if selected_template_id is not None:
        template = await get_template_by_id(db, selected_template_id)
        if template is None or template.company_id != company.id:
            raise conflict_exception("Selected analysis template must belong to the same company.")

    company = await update_company(
        db,
        company,
        CompanyUpdate(
            beeline_api_token=token.strip(),
            beeline_auto_export_enabled=True,
            beeline_auto_analysis_template_id=selected_template_id,
            beeline_last_sync_error=None,
            beeline_last_auto_sync_error=None,
        ),
    )
    if should_run_immediate_sync:
        from src.app.services.beeline_sync import sync_company_beeline_recordings

        await sync_company_beeline_recordings(company.id, ufa_now().date())
        company = await get_manageable_company_or_404(db, current_user, company.id)
    log_info(
        logger,
        "companies.integrations.beeline.set.success",
        actor_user_id=current_user.id,
        company_id=company.id,
        enabled=company.beeline_auto_export_enabled,
        has_token=bool((company.beeline_api_token or "").strip()),
    )
    return build_company_beeline_integration_read(company)


@companies_router.post("/{company_id}/integrations/beeline/sync-range", response_model=CompanyBeelineIntegrationRead)
async def sync_company_beeline_range_route(
    company_id: int,
    payload: CompanyBeelineIntegrationSyncRangePayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CompanyBeelineIntegrationRead:
    log_info(
        logger,
        "companies.integrations.beeline.sync_range.start",
        actor_user_id=current_user.id,
        company_id=company_id,
        date_from=payload.date_from.isoformat(),
        date_to=payload.date_to.isoformat(),
    )
    if payload.date_to < payload.date_from:
        raise conflict_exception("Beeline sync end date must be on or after the start date.")

    company = await get_manageable_company_or_404(db, current_user, company_id)
    if not company.beeline_auto_export_enabled or not (company.beeline_api_token or "").strip():
        raise conflict_exception("Enable the Beeline integration and save a token before loading recordings.")

    from src.app.services.beeline_sync import sync_company_beeline_recordings_range

    await sync_company_beeline_recordings_range(company.id, payload.date_from, payload.date_to)
    company = await get_manageable_company_or_404(db, current_user, company.id)
    log_info(
        logger,
        "companies.integrations.beeline.sync_range.success",
        actor_user_id=current_user.id,
        company_id=company.id,
        date_from=payload.date_from.isoformat(),
        date_to=payload.date_to.isoformat(),
        last_sync_status=company.beeline_last_sync_status,
        last_sync_target_date=company.beeline_last_sync_target_date.isoformat() if company.beeline_last_sync_target_date else None,
    )
    return build_company_beeline_integration_read(company)


@companies_router.post("/{company_id}/integrations/beeline/sync-current-date", response_model=CompanyBeelineIntegrationRead)
async def sync_company_beeline_current_date_route(
    company_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CompanyBeelineIntegrationRead:
    log_info(logger, "companies.integrations.beeline.sync_current_date.start", actor_user_id=current_user.id, company_id=company_id)
    company = await get_manageable_company_or_404(db, current_user, company_id)
    if not company.beeline_auto_export_enabled or not (company.beeline_api_token or "").strip():
        raise conflict_exception("Enable the Beeline integration and save a token before loading current-day recordings.")

    from src.app.services.beeline_sync import sync_company_beeline_recordings

    await sync_company_beeline_recordings(company.id, ufa_now().date())
    company = await get_manageable_company_or_404(db, current_user, company.id)
    log_info(
        logger,
        "companies.integrations.beeline.sync_current_date.success",
        actor_user_id=current_user.id,
        company_id=company.id,
        last_sync_status=company.beeline_last_sync_status,
        last_sync_target_date=company.beeline_last_sync_target_date.isoformat() if company.beeline_last_sync_target_date else None,
    )
    return build_company_beeline_integration_read(company)


@companies_router.delete("/{company_id}/integrations/beeline", response_model=OperationResponse)
async def clear_company_beeline_integration_route(company_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> OperationResponse:
    log_info(logger, "companies.integrations.beeline.clear.start", actor_user_id=current_user.id, company_id=company_id)
    company = await get_manageable_company_or_404(db, current_user, company_id)
    await update_company(
        db,
        company,
        CompanyUpdate(
            beeline_api_token=None,
            beeline_auto_export_enabled=False,
            beeline_auto_analysis_template_id=None,
            beeline_last_sync_error=None,
            beeline_last_sync_status=None,
            beeline_last_auto_sync_error=None,
            beeline_last_auto_sync_status=None,
        ),
    )
    log_info(logger, "companies.integrations.beeline.clear.success", actor_user_id=current_user.id, company_id=company.id)
    return OperationResponse(message="Beeline integration disabled successfully.")


@companies_router.get("/{company_id}/vector-store", response_model=CompanyVectorStoreRead)
async def get_company_vector_store_route(company_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> CompanyVectorStoreRead:
    log_info(logger, "companies.vector_store.get.start", actor_user_id=current_user.id, company_id=company_id)
    company = await get_manageable_company_or_404(db, current_user, company_id)
    log_info(logger, "companies.vector_store.get.success", actor_user_id=current_user.id, company_id=company.id, vector_store_id=company.vector_store_id)
    return build_company_vector_store_read(company.id, company.vector_store_id)


@companies_router.post("/{company_id}/vector-store", response_model=CompanyVectorStoreRead, status_code=status.HTTP_201_CREATED)
async def create_company_vector_store_route(
    company_id: int,
    payload: CompanyVectorStoreCreatePayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CompanyVectorStoreRead:
    log_info(logger, "companies.vector_store.create.start", actor_user_id=current_user.id, company_id=company_id, payload=payload.model_dump())
    company = await get_manageable_company_or_404(db, current_user, company_id)
    if (company.vector_store_id or "").strip():
        raise conflict_exception("Vector store is already configured for this company.")

    vector_store_name = (payload.name or company.name or f"company-{company.id}").strip()

    try:
        vector_store = await vector_store_service.create_vector_store(
            name=vector_store_name,
            metadata={"company_id": str(company.id)},
        )
    except Exception as error:
        log_exception(logger, "companies.vector_store.create.failed", actor_user_id=current_user.id, company_id=company_id, vector_store_name=vector_store_name)
        raise_vector_store_http_error(error)

    company = await update_company(
        db,
        company,
        CompanyUpdate(vector_store_id=vector_store.id),
    )
    log_info(logger, "companies.vector_store.create.success", actor_user_id=current_user.id, company_id=company.id, vector_store_id=company.vector_store_id)
    return build_company_vector_store_read(company.id, company.vector_store_id)


@companies_router.put("/{company_id}/vector-store", response_model=CompanyVectorStoreRead)
async def set_company_vector_store_route(company_id: int, payload: CompanyVectorStoreUpdatePayload, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> CompanyVectorStoreRead:
    log_info(logger, "companies.vector_store.set.start", actor_user_id=current_user.id, company_id=company_id, payload=payload.model_dump())
    company = await get_manageable_company_or_404(db, current_user, company_id)
    company = await update_company(
        db,
        company,
        CompanyUpdate(vector_store_id=payload.vector_store_id),
    )
    log_info(logger, "companies.vector_store.set.success", actor_user_id=current_user.id, company_id=company.id, vector_store_id=company.vector_store_id)
    return build_company_vector_store_read(company.id, company.vector_store_id)


@companies_router.get("/{company_id}/vector-store/files", response_model=list[CompanyVectorStoreFileRead])
async def list_company_vector_store_files_route(
    company_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CompanyVectorStoreFileRead]:
    log_info(logger, "companies.vector_store.files.list.start", actor_user_id=current_user.id, company_id=company_id)
    company = await get_manageable_company_or_404(db, current_user, company_id)
    vector_store_id = ensure_company_has_vector_store(company)

    try:
        vector_store_files = await vector_store_service.list_vector_store_files(vector_store_id=vector_store_id)
    except Exception as error:
        log_exception(logger, "companies.vector_store.files.list.failed", actor_user_id=current_user.id, company_id=company_id, vector_store_id=vector_store_id)
        raise_vector_store_http_error(error)

    filenames: dict[str, str | None] = {}
    for item in vector_store_files:
        try:
            filenames[item.id] = await vector_store_service.resolve_filename(item.id)
        except Exception:
            filenames[item.id] = None

    response_items = [
        build_company_vector_store_file_read(
            file_id=item.id,
            filename=filenames.get(item.id) or item.id,
            status_name=item.status,
            usage_bytes=item.usage_bytes,
            created_at=item.created_at,
            last_error_message=item.last_error.message if item.last_error else None,
        )
        for item in vector_store_files
    ]
    log_info(logger, "companies.vector_store.files.list.success", actor_user_id=current_user.id, company_id=company_id, vector_store_id=vector_store_id, count=len(response_items))
    return response_items


@companies_router.post("/{company_id}/vector-store/files", response_model=CompanyVectorStoreFileBatchRead, status_code=status.HTTP_201_CREATED)
async def upload_company_vector_store_files_route(
    company_id: int,
    files: list[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CompanyVectorStoreFileBatchRead:
    log_info(logger, "companies.vector_store.files.upload.start", actor_user_id=current_user.id, company_id=company_id, file_count=len(files))
    company = await get_manageable_company_or_404(db, current_user, company_id)
    vector_store_id = ensure_company_has_vector_store(company)

    prepared_files: list[tuple[str, bytes, str]] = []
    try:
        for upload in files:
            filename = (upload.filename or "").strip()
            if not filename:
                continue
            contents = await upload.read()
            if not contents:
                continue
            prepared_files.append((filename, contents, upload.content_type or "application/octet-stream"))

        if not prepared_files:
            raise ValueError("Select at least one non-empty file to upload.")

        batch = await vector_store_service.upload_files(
            vector_store_id=vector_store_id,
            files=prepared_files,
        )
    except Exception as error:
        log_exception(logger, "companies.vector_store.files.upload.failed", actor_user_id=current_user.id, company_id=company_id, vector_store_id=vector_store_id)
        raise_vector_store_http_error(error)
    finally:
        for upload in files:
            await upload.close()

    log_info(
        logger,
        "companies.vector_store.files.upload.success",
        actor_user_id=current_user.id,
        company_id=company_id,
        vector_store_id=vector_store_id,
        uploaded_count=batch.file_counts.total,
        completed_count=batch.file_counts.completed,
        failed_count=batch.file_counts.failed,
    )
    return build_company_vector_store_file_batch_read(batch)


@companies_router.delete("/{company_id}/vector-store", response_model=OperationResponse)
async def clear_company_vector_store_route(company_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> OperationResponse:
    log_info(logger, "companies.vector_store.clear.start", actor_user_id=current_user.id, company_id=company_id)
    company = await get_manageable_company_or_404(db, current_user, company_id)
    await update_company(
        db,
        company,
        CompanyUpdate(vector_store_id=None),
    )
    log_info(logger, "companies.vector_store.clear.success", actor_user_id=current_user.id, company_id=company.id)
    return OperationResponse(message="Company vector store cleared successfully.")


@companies_router.patch("/{company_id}", response_model=CompanyRead)
async def update_company_route(company_id: int, payload: CompanyUpdatePayload, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> CompanyRead:
    changes = payload.model_dump(exclude_unset=True)
    log_info(logger, "companies.update.start", actor_user_id=current_user.id, company_id=company_id, changes=changes)
    company = await get_manageable_company_or_404(db, current_user, company_id)
    try:
        company = await update_company(
            db,
            company,
            CompanyUpdate(**changes),
        )
    except IntegrityError as exc:
        log_exception(logger, "companies.update.conflict", actor_user_id=current_user.id, company_id=company_id)
        raise conflict_exception("Company with this name already exists.") from exc
    log_info(logger, "companies.update.success", actor_user_id=current_user.id, company_id=company.id)
    return CompanyRead.model_validate(company)


@companies_router.delete("/{company_id}", response_model=OperationResponse)
async def delete_company_route(company_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> OperationResponse:
    log_info(logger, "companies.delete.start", actor_user_id=current_user.id, company_id=company_id)
    company = await get_manageable_company_or_404(db, current_user, company_id)
    await delete_company(db, company)
    log_info(logger, "companies.delete.success", actor_user_id=current_user.id, company_id=company_id)
    return OperationResponse(message="Company deleted successfully.")
