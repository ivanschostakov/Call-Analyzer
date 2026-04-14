import logging as py_logging

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.app.observability import log_info
from src.database.models import Employee
from src.database.schemas import EmployeeCreate, EmployeeUpdate

logger = py_logging.getLogger(__name__)


async def create_employee(db: AsyncSession, payload: EmployeeCreate) -> Employee:
    log_info(logger, "crud.employees.create.start", payload=payload.model_dump())
    employee = Employee(**payload.model_dump())
    db.add(employee)
    await db.commit()
    saved_employee = await get_employee_by_id(db, employee.id)
    if saved_employee is None:
        raise RuntimeError("Created employee could not be reloaded.")
    log_info(logger, "crud.employees.create.success", employee_id=saved_employee.id, company_id=saved_employee.company_id, user_id=saved_employee.user_id)
    return saved_employee


async def get_employee_by_id(db: AsyncSession, employee_id: int) -> Employee | None:
    statement = select(Employee).options(selectinload(Employee.user), selectinload(Employee.manager)).where(Employee.id == employee_id)
    employee = (await db.execute(statement)).scalar_one_or_none()
    log_info(logger, "crud.employees.get_by_id", employee_id=employee_id, found=bool(employee))
    return employee


async def get_employee_by_company_id_and_user_id(db: AsyncSession, company_id: int, user_id: int) -> Employee | None:
    statement = (
        select(Employee)
        .options(selectinload(Employee.user), selectinload(Employee.manager))
        .where(Employee.company_id == company_id, Employee.user_id == user_id)
    )
    employee = (await db.execute(statement)).scalar_one_or_none()
    log_info(logger, "crud.employees.get_by_company_and_user", company_id=company_id, user_id=user_id, found=bool(employee))
    return employee


async def list_employees_by_company_id(db: AsyncSession, company_id: int) -> list[Employee]:
    statement = (
        select(Employee)
        .options(selectinload(Employee.user), selectinload(Employee.manager))
        .where(Employee.company_id == company_id)
        .order_by(Employee.created_at.asc())
    )
    items = list((await db.execute(statement)).scalars().all())
    log_info(logger, "crud.employees.list_by_company", company_id=company_id, count=len(items))
    return items


async def list_employees_by_company_id_and_manager_user_id(db: AsyncSession, company_id: int, manager_user_id: int) -> list[Employee]:
    statement = (
        select(Employee)
        .options(selectinload(Employee.user), selectinload(Employee.manager))
        .where(Employee.company_id == company_id, Employee.manager_user_id == manager_user_id)
        .order_by(Employee.created_at.asc())
    )
    items = list((await db.execute(statement)).scalars().all())
    log_info(logger, "crud.employees.list_by_company_and_manager", company_id=company_id, manager_user_id=manager_user_id, count=len(items))
    return items


async def list_employees_by_user_id(db: AsyncSession, user_id: int) -> list[Employee]:
    statement = (
        select(Employee)
        .options(selectinload(Employee.user), selectinload(Employee.manager))
        .where(Employee.user_id == user_id)
        .order_by(Employee.created_at.asc())
    )
    items = list((await db.execute(statement)).scalars().all())
    log_info(logger, "crud.employees.list_by_user", user_id=user_id, count=len(items))
    return items


async def update_employee(db: AsyncSession, employee: Employee, payload: EmployeeUpdate) -> Employee:
    changes = payload.model_dump(exclude_unset=True)
    log_info(logger, "crud.employees.update.start", employee_id=employee.id, changes=changes)
    for field, value in changes.items():
        if field == "user_role":
            continue
        setattr(employee, field, value)

    db.add(employee)
    await db.commit()
    saved_employee = await get_employee_by_id(db, employee.id)
    if saved_employee is None:
        raise RuntimeError("Updated employee could not be reloaded.")
    log_info(logger, "crud.employees.update.success", employee_id=saved_employee.id, company_id=saved_employee.company_id, user_id=saved_employee.user_id)
    return saved_employee


async def clear_manager_for_company_employees(db: AsyncSession, company_id: int, manager_user_id: int) -> None:
    statement = (
        update(Employee)
        .where(Employee.company_id == company_id, Employee.manager_user_id == manager_user_id)
        .values(manager_user_id=None)
    )
    await db.execute(statement)
    await db.commit()
    log_info(logger, "crud.employees.clear_manager", company_id=company_id, manager_user_id=manager_user_id)


async def delete_employee(db: AsyncSession, employee: Employee) -> None:
    await db.delete(employee)
    await db.commit()
    log_info(logger, "crud.employees.delete", employee_id=employee.id, company_id=employee.company_id, user_id=employee.user_id)
