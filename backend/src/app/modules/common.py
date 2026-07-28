from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from src.database.crud import (
    get_analysis_by_id,
    get_company_by_id,
    get_criterion_by_id,
    get_employee_by_company_id_and_user_id,
    get_employee_by_id,
    list_employees_by_company_id_and_manager_user_id,
    get_template_by_id,
    get_transcription_by_id,
    get_user_by_id,
)
from src.database.models import Analysis, Company, Criterion, Employee, Template, Transcription, User
from src.enums import UserRole


class OperationResponse(BaseModel):
    ok: bool = True
    message: str


def conflict_exception(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


def forbidden_exception(detail: str = "You do not have permission to perform this action.") -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def is_admin(user: User) -> bool:
    return user.role == UserRole.ADMIN


def is_owner(user: User, company: Company) -> bool:
    return company.owner_id == user.id


def normalize_email_address(email: str) -> str:
    return email.lower().strip()


def build_user_display_name(user: User | None) -> str | None:
    if user is None:
        return None
    full_name = " ".join(part for part in [user.name, user.surname] if part).strip()
    return full_name or user.email


def is_transcription_visible_to_user_ids(
    transcription: Transcription,
    visible_user_ids: list[int] | None,
) -> bool:
    if visible_user_ids is None:
        return True
    if transcription.detected_employee_user_id is not None:
        return transcription.detected_employee_user_id in visible_user_ids
    return transcription.uploaded_by_user_id in visible_user_ids


def is_analysis_visible_to_user_ids(
    analysis: Analysis,
    visible_user_ids: list[int] | None,
) -> bool:
    if visible_user_ids is None:
        return True
    if analysis.transcription is not None:
        return is_transcription_visible_to_user_ids(analysis.transcription, visible_user_ids)
    return analysis.created_by_user_id in visible_user_ids


def can_manage_company(current_user: User, company: Company) -> bool:
    return is_admin(current_user) or is_owner(current_user, company)


async def can_manage_team(db: AsyncSession, current_user: User, company: Company) -> bool:
    if can_manage_company(current_user, company):
        return True
    if not is_admin(current_user):
        return False
    membership = await get_employee_by_company_id_and_user_id(db, company.id, current_user.id)
    return membership is not None


async def get_visible_user_ids_for_company(db: AsyncSession, current_user: User, company: Company) -> list[int] | None:
    if can_manage_company(current_user, company):
        return None

    if is_admin(current_user):
        direct_reports = await list_employees_by_company_id_and_manager_user_id(db, company.id, current_user.id)
        return sorted({current_user.id, *(item.user_id for item in direct_reports)})

    return [current_user.id]


async def is_company_member(db: AsyncSession, current_user: User, company_id: int) -> bool:
    membership = await get_employee_by_company_id_and_user_id(db, company_id, current_user.id)
    return membership is not None


async def ensure_can_create_company(current_user: User) -> None:
    if current_user.role not in {UserRole.OWNER, UserRole.ADMIN}:
        raise forbidden_exception("Only company owners and administrators can create companies.")


async def get_accessible_company_or_404(db: AsyncSession, current_user: User, company_id: int) -> Company:
    company = await get_company_by_id(db, company_id)
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found.")
    if can_manage_company(current_user, company):
        return company
    if await is_company_member(db, current_user, company_id):
        return company
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found.")


async def get_manageable_company_or_404(db: AsyncSession, current_user: User, company_id: int) -> Company:
    company = await get_company_by_id(db, company_id)
    if company is None or not can_manage_company(current_user, company):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found.")
    return company


async def get_owned_company_or_404(db: AsyncSession, current_user: User, company_id: int) -> Company:
    company = await get_company_by_id(db, company_id)
    if company is None or not is_owner(current_user, company):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found.")
    return company


async def get_team_manageable_company_or_404(db: AsyncSession, current_user: User, company_id: int) -> Company:
    company = await get_accessible_company_or_404(db, current_user, company_id)
    if await can_manage_team(db, current_user, company):
        return company
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found.")


async def get_accessible_template_or_404(db: AsyncSession, current_user: User, template_id: int) -> Template:
    template = await get_template_by_id(db, template_id)
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found.")
    await get_accessible_company_or_404(db, current_user, template.company_id)
    return template


async def get_manageable_template_or_404(db: AsyncSession, current_user: User, template_id: int) -> Template:
    template = await get_template_by_id(db, template_id)
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found.")
    await get_manageable_company_or_404(db, current_user, template.company_id)
    return template


async def get_accessible_transcription_or_404(db: AsyncSession, current_user: User, transcription_id: int) -> Transcription:
    transcription = await get_transcription_by_id(db, transcription_id)
    if transcription is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transcription not found.")
    company = await get_accessible_company_or_404(db, current_user, transcription.company_id)
    visible_user_ids = await get_visible_user_ids_for_company(db, current_user, company)
    if is_transcription_visible_to_user_ids(transcription, visible_user_ids):
        return transcription
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transcription not found.")


async def get_manageable_analysis_company_or_404(db: AsyncSession, current_user: User, company_id: int) -> Company:
    return await get_accessible_company_or_404(db, current_user, company_id)


async def get_accessible_analysis_or_404(db: AsyncSession, current_user: User, analysis_id: int) -> Analysis:
    analysis = await get_analysis_by_id(db, analysis_id)
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found.")

    company = await get_accessible_company_or_404(db, current_user, analysis.company_id)
    visible_user_ids = await get_visible_user_ids_for_company(db, current_user, company)
    if is_analysis_visible_to_user_ids(analysis, visible_user_ids):
        return analysis
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found.")


async def get_accessible_criterion_or_404(db: AsyncSession, current_user: User, criterion_id: int) -> Criterion:
    criterion = await get_criterion_by_id(db, criterion_id)
    if criterion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Criterion not found.")
    await get_accessible_template_or_404(db, current_user, criterion.template_id)
    return criterion


async def get_manageable_criterion_or_404(db: AsyncSession, current_user: User, criterion_id: int) -> Criterion:
    criterion = await get_criterion_by_id(db, criterion_id)
    if criterion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Criterion not found.")
    await get_manageable_template_or_404(db, current_user, criterion.template_id)
    return criterion


async def get_accessible_employee_or_404(db: AsyncSession, current_user: User, employee_id: int) -> Employee:
    employee = await get_employee_by_id(db, employee_id)
    if employee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found.")
    company = await get_accessible_company_or_404(db, current_user, employee.company_id)
    if can_manage_company(current_user, company):
        return employee
    if is_admin(current_user) and (employee.user_id == current_user.id or employee.manager_user_id == current_user.id):
        return employee
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found.")


async def get_existing_user_or_404(db: AsyncSession, user_id: int) -> User:
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return user
