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
    get_accessible_criterion_or_404,
    get_accessible_template_or_404,
    get_manageable_criterion_or_404,
    get_manageable_template_or_404,
)
from src.database import get_db
from src.database.crud import create_criterion, delete_criterion, list_criteria_by_template_id, update_criterion
from src.database.models import User
from src.database.schemas import CriterionCreate, CriterionRead, CriterionUpdate

criteria_router = APIRouter(prefix="/criteria", tags=["criteria"])
logger = logging.getLogger(__name__)


@criteria_router.get("", response_model=list[CriterionRead])
async def list_criteria_route(template_id: int = Query(...), current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> list[CriterionRead]:
    log_info(logger, "criteria.list.start", actor_user_id=current_user.id, template_id=template_id)
    await get_accessible_template_or_404(db, current_user, template_id)
    items = await list_criteria_by_template_id(db, template_id)
    log_info(logger, "criteria.list.success", actor_user_id=current_user.id, template_id=template_id, count=len(items))
    return [CriterionRead.model_validate(item) for item in items]


@criteria_router.post("", response_model=CriterionRead, status_code=status.HTTP_201_CREATED)
async def create_criterion_route(payload: CriterionCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> CriterionRead:
    log_info(logger, "criteria.create.start", actor_user_id=current_user.id, payload=payload.model_dump())
    await get_manageable_template_or_404(db, current_user, payload.template_id)
    try: criterion = await create_criterion(db, payload)
    except IntegrityError as exc: raise conflict_exception("Criterion with this name or position already exists for this template.") from exc
    log_info(logger, "criteria.create.success", actor_user_id=current_user.id, criterion_id=criterion.id, template_id=criterion.template_id)
    return CriterionRead.model_validate(criterion)


@criteria_router.get("/{criterion_id}", response_model=CriterionRead)
async def get_criterion_route(criterion_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> CriterionRead:
    log_info(logger, "criteria.get.start", actor_user_id=current_user.id, criterion_id=criterion_id)
    criterion = await get_accessible_criterion_or_404(db, current_user, criterion_id)
    log_info(logger, "criteria.get.success", actor_user_id=current_user.id, criterion_id=criterion.id, template_id=criterion.template_id)
    return CriterionRead.model_validate(criterion)


@criteria_router.patch("/{criterion_id}", response_model=CriterionRead)
async def update_criterion_route(criterion_id: int, payload: CriterionUpdate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> CriterionRead:
    log_info(logger, "criteria.update.start", actor_user_id=current_user.id, criterion_id=criterion_id, changes=payload.model_dump(exclude_unset=True))
    criterion = await get_manageable_criterion_or_404(db, current_user, criterion_id)
    if payload.template_id is not None: await get_manageable_template_or_404(db, current_user, payload.template_id)
    try: criterion = await update_criterion(db, criterion, payload)
    except IntegrityError as exc: raise conflict_exception("Criterion with this name or position already exists for this template.") from exc
    log_info(logger, "criteria.update.success", actor_user_id=current_user.id, criterion_id=criterion.id, template_id=criterion.template_id)
    return CriterionRead.model_validate(criterion)


@criteria_router.delete("/{criterion_id}", response_model=OperationResponse)
async def delete_criterion_route(criterion_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> OperationResponse:
    log_info(logger, "criteria.delete.start", actor_user_id=current_user.id, criterion_id=criterion_id)
    criterion = await get_manageable_criterion_or_404(db, current_user, criterion_id)
    await delete_criterion(db, criterion)
    log_info(logger, "criteria.delete.success", actor_user_id=current_user.id, criterion_id=criterion_id, template_id=criterion.template_id)
    return OperationResponse(message="Criterion deleted successfully.")
