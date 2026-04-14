import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from src.app.observability import log_info
from src.app.modules.auth.dependencies import get_current_user
from src.app.modules.common import (
    OperationResponse,
    conflict_exception,
    get_accessible_company_or_404,
    get_accessible_template_or_404,
    get_manageable_company_or_404,
    get_manageable_template_or_404,
)
from src.database import get_db
from src.database.crud import create_template, delete_template, list_templates_by_company_id, update_template
from src.database.models import User
from src.database.schemas import TemplateCreate, TemplateRead, TemplateUpdate

templates_router = APIRouter(prefix="/templates", tags=["templates"])
logger = logging.getLogger(__name__)


@templates_router.get("", response_model=list[TemplateRead])
async def list_templates_route(company_id: int = Query(...), current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> list[TemplateRead]:
    log_info(logger, "templates.list.start", actor_user_id=current_user.id, company_id=company_id)
    await get_accessible_company_or_404(db, current_user, company_id)
    items = await list_templates_by_company_id(db, company_id)
    log_info(logger, "templates.list.success", actor_user_id=current_user.id, company_id=company_id, count=len(items))
    return [TemplateRead.model_validate(item) for item in items]


@templates_router.post("", response_model=TemplateRead, status_code=status.HTTP_201_CREATED)
async def create_template_route(payload: TemplateCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> TemplateRead:
    log_info(logger, "templates.create.start", actor_user_id=current_user.id, payload=payload.model_dump())
    await get_manageable_company_or_404(db, current_user, payload.company_id)
    try: template = await create_template(db, payload)
    except IntegrityError as exc: raise conflict_exception("Template with this name already exists for this company.") from exc
    log_info(logger, "templates.create.success", actor_user_id=current_user.id, template_id=template.id, company_id=template.company_id)
    return TemplateRead.model_validate(template)


@templates_router.get("/{template_id}", response_model=TemplateRead)
async def get_template_route(template_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> TemplateRead:
    log_info(logger, "templates.get.start", actor_user_id=current_user.id, template_id=template_id)
    template = await get_accessible_template_or_404(db, current_user, template_id)
    log_info(logger, "templates.get.success", actor_user_id=current_user.id, template_id=template.id, company_id=template.company_id)
    return TemplateRead.model_validate(template)


@templates_router.patch("/{template_id}", response_model=TemplateRead)
async def update_template_route(template_id: int, payload: TemplateUpdate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> TemplateRead:
    log_info(logger, "templates.update.start", actor_user_id=current_user.id, template_id=template_id, changes=payload.model_dump(exclude_unset=True))
    template = await get_manageable_template_or_404(db, current_user, template_id)
    if payload.company_id is not None: await get_manageable_company_or_404(db, current_user, payload.company_id)
    try: template = await update_template(db, template, payload)
    except IntegrityError as exc: raise conflict_exception("Template with this name already exists for this company.") from exc
    log_info(logger, "templates.update.success", actor_user_id=current_user.id, template_id=template.id, company_id=template.company_id)
    return TemplateRead.model_validate(template)


@templates_router.delete("/{template_id}", response_model=OperationResponse)
async def delete_template_route(template_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> OperationResponse:
    log_info(logger, "templates.delete.start", actor_user_id=current_user.id, template_id=template_id)
    template = await get_manageable_template_or_404(db, current_user, template_id)
    await delete_template(db, template)
    log_info(logger, "templates.delete.success", actor_user_id=current_user.id, template_id=template_id, company_id=template.company_id)
    return OperationResponse(message="Template deleted successfully.")
