import logging as py_logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.enums import DEFAULT_COMPANY_TEMPLATE
from src.app.observability import log_info
from src.database.models import Criterion, Template
from src.database.schemas import TemplateCreate, TemplateUpdate

logger = py_logging.getLogger(__name__)


async def create_template(db: AsyncSession, payload: TemplateCreate) -> Template:
    log_info(logger, "crud.templates.create.start", payload=payload.model_dump())
    template = Template(**payload.model_dump())
    db.add(template)
    await db.commit()
    await db.refresh(template)
    log_info(logger, "crud.templates.create.success", template_id=template.id, company_id=template.company_id, name=template.name)
    return template


def build_default_company_criteria(template_id: int) -> list[Criterion]:
    return [
        Criterion(
            template_id=template_id,
            name=criterion.name,
            description=criterion.description,
            prompt=criterion.prompt,
            answer_type=criterion.answer_type,
            position=criterion.position,
        )
        for criterion in DEFAULT_COMPANY_TEMPLATE.criteria
    ]


async def get_default_template_by_company_id(db: AsyncSession, company_id: int) -> Template | None:
    statement = select(Template).where(
        Template.company_id == company_id,
        Template.name == DEFAULT_COMPANY_TEMPLATE.name,
    )
    return (await db.execute(statement)).scalar_one_or_none()


async def create_default_template_for_company(db: AsyncSession, company_id: int) -> Template:
    log_info(logger, "crud.templates.default.create.start", company_id=company_id)
    template = Template(
        company_id=company_id,
        name=DEFAULT_COMPANY_TEMPLATE.name,
        description=DEFAULT_COMPANY_TEMPLATE.description,
        instructions=DEFAULT_COMPANY_TEMPLATE.instructions,
    )
    db.add(template)
    await db.flush()

    db.add_all(build_default_company_criteria(template.id))
    await db.flush()
    log_info(logger, "crud.templates.default.create.success", company_id=company_id, template_id=template.id)
    return template


async def ensure_default_template_metadata(db: AsyncSession, template: Template) -> None:
    should_update = False

    if template.description is None:
        template.description = DEFAULT_COMPANY_TEMPLATE.description
        should_update = True

    if not template.instructions:
        template.instructions = DEFAULT_COMPANY_TEMPLATE.instructions
        should_update = True

    if should_update:
        db.add(template)
        await db.flush()


async def ensure_default_criteria_for_template(db: AsyncSession, template_id: int) -> None:
    statement = select(Criterion.name, Criterion.position).where(Criterion.template_id == template_id)
    existing_pairs = (await db.execute(statement)).all()
    existing_names = {name for name, _ in existing_pairs}
    existing_positions = {position for _, position in existing_pairs}
    missing_criteria = [
        Criterion(
            template_id=template_id,
            name=criterion.name,
            description=criterion.description,
            prompt=criterion.prompt,
            answer_type=criterion.answer_type,
            position=criterion.position,
        )
        for criterion in DEFAULT_COMPANY_TEMPLATE.criteria
        if criterion.name not in existing_names and criterion.position not in existing_positions
    ]
    if missing_criteria:
        db.add_all(missing_criteria)
        await db.flush()


async def ensure_default_template_for_company(db: AsyncSession, company_id: int) -> Template:
    template = await get_default_template_by_company_id(db, company_id)
    if template is None:
        return await create_default_template_for_company(db, company_id)

    await ensure_default_template_metadata(db, template)
    await ensure_default_criteria_for_template(db, template.id)
    return template


async def get_template_by_id(db: AsyncSession, template_id: int) -> Template | None:
    template = await db.get(Template, template_id)
    log_info(logger, "crud.templates.get_by_id", template_id=template_id, found=bool(template))
    return template


async def list_templates_by_company_id(db: AsyncSession, company_id: int) -> list[Template]:
    statement = select(Template).where(Template.company_id == company_id).order_by(Template.updated_at.desc())
    items = list((await db.execute(statement)).scalars().all())
    log_info(logger, "crud.templates.list_by_company", company_id=company_id, count=len(items))
    return items


async def update_template(db: AsyncSession, template: Template, payload: TemplateUpdate) -> Template:
    changes = payload.model_dump(exclude_unset=True)
    log_info(logger, "crud.templates.update.start", template_id=template.id, changes=changes)
    for field, value in changes.items():
        setattr(template, field, value)

    db.add(template)
    await db.commit()
    await db.refresh(template)
    log_info(logger, "crud.templates.update.success", template_id=template.id, company_id=template.company_id)
    return template


async def delete_template(db: AsyncSession, template: Template) -> None:
    await db.delete(template)
    await db.commit()
    log_info(logger, "crud.templates.delete", template_id=template.id, company_id=template.company_id)
