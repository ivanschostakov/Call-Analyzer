import logging as py_logging

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.observability import log_info
from src.database.models import Company, Employee
from src.database.crud.templates import create_default_template_for_company
from src.database.schemas import CompanyCreate, CompanyUpdate

logger = py_logging.getLogger(__name__)


async def create_company(db: AsyncSession, payload: CompanyCreate) -> Company:
    log_info(logger, "crud.companies.create.start", payload=payload.model_dump())
    company = Company(**payload.model_dump())
    db.add(company)
    await db.flush()
    await create_default_template_for_company(db, company.id)
    await db.commit()
    await db.refresh(company)
    log_info(logger, "crud.companies.create.success", company_id=company.id, owner_id=company.owner_id, name=company.name)
    return company


async def get_company_by_id(db: AsyncSession, company_id: int) -> Company | None:
    company = await db.get(Company, company_id)
    log_info(logger, "crud.companies.get_by_id", company_id=company_id, found=bool(company))
    return company


async def list_companies(db: AsyncSession) -> list[Company]:
    statement = select(Company).order_by(Company.updated_at.desc())
    items = list((await db.execute(statement)).scalars().all())
    log_info(logger, "crud.companies.list", count=len(items))
    return items


async def list_companies_by_owner_id(db: AsyncSession, owner_id: int) -> list[Company]:
    statement = select(Company).where(Company.owner_id == owner_id).order_by(Company.updated_at.desc())
    items = list((await db.execute(statement)).scalars().all())
    log_info(logger, "crud.companies.list_by_owner", owner_id=owner_id, count=len(items))
    return items


def build_list_companies_accessible_to_user_id_statement(user_id: int):
    return (
        select(Company)
        .where(
            or_(
                Company.owner_id == user_id,
                Company.employees.any(Employee.user_id == user_id),
            )
        )
        .order_by(Company.updated_at.desc())
    )


async def list_companies_accessible_to_user_id(db: AsyncSession, user_id: int) -> list[Company]:
    statement = build_list_companies_accessible_to_user_id_statement(user_id)
    items = list((await db.execute(statement)).scalars().all())
    log_info(logger, "crud.companies.list_accessible", user_id=user_id, count=len(items))
    return items


async def list_companies_with_beeline_auto_export_enabled(db: AsyncSession) -> list[Company]:
    statement = (
        select(Company)
        .where(
            Company.beeline_auto_export_enabled.is_(True),
            Company.beeline_api_token.is_not(None),
        )
        .order_by(Company.id.asc())
    )
    items = list((await db.execute(statement)).scalars().all())
    log_info(logger, "crud.companies.list_beeline_auto_export_enabled", count=len(items))
    return items


async def update_company(db: AsyncSession, company: Company, payload: CompanyUpdate) -> Company:
    changes = payload.model_dump(exclude_unset=True)
    log_info(logger, "crud.companies.update.start", company_id=company.id, changes=changes)
    for field, value in changes.items():
        setattr(company, field, value)

    db.add(company)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    await db.refresh(company)
    log_info(logger, "crud.companies.update.success", company_id=company.id)
    return company


async def delete_company(db: AsyncSession, company: Company) -> None:
    await db.delete(company)
    await db.commit()
    log_info(logger, "crud.companies.delete", company_id=company.id, owner_id=company.owner_id)
