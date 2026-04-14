from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from config import ufa_now
from src.app.modules.common import build_user_display_name, conflict_exception, normalize_email_address
from src.database.crud import get_employee_by_company_id_and_user_id, get_employee_invitation_by_token
from src.database.models import Employee, EmployeeInvitation, User
from src.database.schemas import EmployeeInvitationRead, EmployeeRead
from src.enums import UserRole


def build_employee_read(employee: Employee) -> EmployeeRead:
    return EmployeeRead(
        id=employee.id,
        user_id=employee.user_id,
        company_id=employee.company_id,
        manager_user_id=employee.manager_user_id,
        user_role=employee.user.role if employee.user else None,
        user_display_name=build_user_display_name(employee.user),
        user_email=employee.user.email if employee.user else None,
        manager_display_name=build_user_display_name(employee.manager),
        manager_email=employee.manager.email if employee.manager else None,
        created_at=employee.created_at,
        updated_at=employee.updated_at,
    )


def build_employee_invitation_read(invitation: EmployeeInvitation) -> EmployeeInvitationRead:
    if invitation.accepted_at is not None:
        status_value = "accepted"
    elif invitation.expires_at <= ufa_now():
        status_value = "expired"
    else:
        status_value = "pending"

    return EmployeeInvitationRead(
        id=invitation.id,
        company_id=invitation.company_id,
        company_name=invitation.company.name if invitation.company else "",
        email=invitation.email,
        invited_by_user_id=invitation.invited_by_user_id,
        invited_by_display_name=build_user_display_name(invitation.invited_by),
        invited_by_email=invitation.invited_by.email if invitation.invited_by else None,
        accepted_by_user_id=invitation.accepted_by_user_id,
        accepted_by_display_name=build_user_display_name(invitation.accepted_by),
        accepted_by_email=invitation.accepted_by.email if invitation.accepted_by else None,
        accepted_at=invitation.accepted_at,
        expires_at=invitation.expires_at,
        status=status_value,
        created_at=invitation.created_at,
        updated_at=invitation.updated_at,
    )


def ensure_invitation_is_usable(invitation: EmployeeInvitation | None, email: str | None = None) -> EmployeeInvitation:
    if invitation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found.")
    if invitation.accepted_at is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invitation has already been accepted.")
    if invitation.expires_at <= ufa_now():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invitation has expired.")
    if email is not None and normalize_email_address(email) != invitation.email:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invitation email does not match the current user.")
    return invitation


async def accept_employee_invitation_for_user(db: AsyncSession, *, token: str, user: User) -> EmployeeInvitation:
    invitation = ensure_invitation_is_usable(await get_employee_invitation_by_token(db, token), user.email)

    existing_membership = await get_employee_by_company_id_and_user_id(db, invitation.company_id, user.id)
    if existing_membership is None:
        db.add(Employee(user_id=user.id, company_id=invitation.company_id, manager_user_id=None))

    invitation.accepted_by_user_id = user.id
    invitation.accepted_at = ufa_now()
    db.add(invitation)
    await db.commit()

    refreshed = await get_employee_invitation_by_token(db, token)
    if refreshed is None:
        raise RuntimeError("Accepted invitation could not be reloaded.")
    return refreshed


async def validate_manager_assignment(
    db: AsyncSession,
    *,
    company_id: int,
    employee_user_id: int,
    manager_user_id: int | None,
) -> int | None:
    if manager_user_id is None:
        return None
    if manager_user_id == employee_user_id:
        raise conflict_exception("Employee cannot manage themselves.")

    manager_membership = await get_employee_by_company_id_and_user_id(db, company_id, manager_user_id)
    if manager_membership is None or manager_membership.user is None:
        raise conflict_exception("Selected manager must belong to the same company.")
    if manager_membership.user.role != UserRole.ADMIN:
        raise conflict_exception("Selected manager must have the administrator role.")

    return manager_user_id


__all__ = [
    "build_employee_read",
    "build_employee_invitation_read",
    "ensure_invitation_is_usable",
    "accept_employee_invitation_for_user",
    "validate_manager_assignment",
]
