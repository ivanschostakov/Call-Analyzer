import logging as py_logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.observability import log_info
from src.database.models import Criterion
from src.database.schemas import CriterionCreate, CriterionUpdate

logger = py_logging.getLogger(__name__)


async def create_criterion(db: AsyncSession, payload: CriterionCreate) -> Criterion:
    log_info(logger, "crud.criteria.create.start", payload=payload.model_dump())
    criterion = Criterion(**payload.model_dump())
    db.add(criterion)
    await db.commit()
    await db.refresh(criterion)
    log_info(logger, "crud.criteria.create.success", criterion_id=criterion.id, template_id=criterion.template_id)
    return criterion


async def get_criterion_by_id(db: AsyncSession, criterion_id: int) -> Criterion | None:
    criterion = await db.get(Criterion, criterion_id)
    log_info(logger, "crud.criteria.get_by_id", criterion_id=criterion_id, found=bool(criterion))
    return criterion


async def list_criteria_by_template_id(db: AsyncSession, template_id: int) -> list[Criterion]:
    statement = select(Criterion).where(Criterion.template_id == template_id).order_by(Criterion.position.asc(), Criterion.id.asc())
    items = list((await db.execute(statement)).scalars().all())
    log_info(logger, "crud.criteria.list_by_template", template_id=template_id, count=len(items))
    return items


async def update_criterion(db: AsyncSession, criterion: Criterion, payload: CriterionUpdate) -> Criterion:
    changes = payload.model_dump(exclude_unset=True)
    log_info(logger, "crud.criteria.update.start", criterion_id=criterion.id, changes=changes)
    for field, value in changes.items():
        setattr(criterion, field, value)

    db.add(criterion)
    await db.commit()
    await db.refresh(criterion)
    log_info(logger, "crud.criteria.update.success", criterion_id=criterion.id, template_id=criterion.template_id)
    return criterion


async def delete_criterion(db: AsyncSession, criterion: Criterion) -> None:
    await db.delete(criterion)
    await db.commit()
    log_info(logger, "crud.criteria.delete", criterion_id=criterion.id, template_id=criterion.template_id)
