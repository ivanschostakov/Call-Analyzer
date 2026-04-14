import logging as py_logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config import ufa_now
from src.app.observability import log_info
from src.database.models import EmployeeInvitation

logger = py_logging.getLogger(__name__)


async def create_employee_invitation(db: AsyncSession, invitation: EmployeeInvitation) -> EmployeeInvitation:
    log_info(logger, "crud.employee_invitations.create.start", invitation=invitation)
    db.add(invitation)
    await db.commit()
    await db.refresh(invitation)
    log_info(logger, "crud.employee_invitations.create.success", invitation_id=invitation.id, company_id=invitation.company_id, email=invitation.email)
    return invitation


async def get_employee_invitation_by_id(db: AsyncSession, invitation_id: int) -> EmployeeInvitation | None:
    statement = (
        select(EmployeeInvitation)
        .options(
            selectinload(EmployeeInvitation.company),
            selectinload(EmployeeInvitation.invited_by),
            selectinload(EmployeeInvitation.accepted_by),
        )
        .where(EmployeeInvitation.id == invitation_id)
    )
    invitation = (await db.execute(statement)).scalar_one_or_none()
    log_info(logger, "crud.employee_invitations.get_by_id", invitation_id=invitation_id, found=bool(invitation))
    return invitation


async def get_employee_invitation_by_token(db: AsyncSession, token: str) -> EmployeeInvitation | None:
    statement = (
        select(EmployeeInvitation)
        .options(
            selectinload(EmployeeInvitation.company),
            selectinload(EmployeeInvitation.invited_by),
            selectinload(EmployeeInvitation.accepted_by),
        )
        .where(EmployeeInvitation.token == token)
    )
    invitation = (await db.execute(statement)).scalar_one_or_none()
    log_info(logger, "crud.employee_invitations.get_by_token", invitation_token=token, found=bool(invitation))
    return invitation


async def get_active_employee_invitation_by_company_id_and_email(db: AsyncSession, company_id: int, email: str) -> EmployeeInvitation | None:
    statement = (
        select(EmployeeInvitation)
        .options(
            selectinload(EmployeeInvitation.company),
            selectinload(EmployeeInvitation.invited_by),
            selectinload(EmployeeInvitation.accepted_by),
        )
        .where(
            EmployeeInvitation.company_id == company_id,
            EmployeeInvitation.email == email,
            EmployeeInvitation.accepted_at.is_(None),
            EmployeeInvitation.expires_at > ufa_now(),
        )
        .order_by(EmployeeInvitation.created_at.desc(), EmployeeInvitation.id.desc())
    )
    invitation = (await db.execute(statement)).scalars().first()
    log_info(logger, "crud.employee_invitations.get_active", company_id=company_id, email=email, found=bool(invitation))
    return invitation


async def list_employee_invitations_by_company_id(db: AsyncSession, company_id: int) -> list[EmployeeInvitation]:
    statement = (
        select(EmployeeInvitation)
        .options(
            selectinload(EmployeeInvitation.company),
            selectinload(EmployeeInvitation.invited_by),
            selectinload(EmployeeInvitation.accepted_by),
        )
        .where(EmployeeInvitation.company_id == company_id)
        .order_by(EmployeeInvitation.created_at.desc(), EmployeeInvitation.id.desc())
    )
    items = list((await db.execute(statement)).scalars().all())
    log_info(logger, "crud.employee_invitations.list_by_company", company_id=company_id, count=len(items))
    return items


async def update_employee_invitation(db: AsyncSession, invitation: EmployeeInvitation) -> EmployeeInvitation:
    db.add(invitation)
    await db.commit()
    await db.refresh(invitation)
    log_info(logger, "crud.employee_invitations.update", invitation_id=invitation.id, company_id=invitation.company_id, accepted_at=invitation.accepted_at)
    return invitation


async def delete_employee_invitation(db: AsyncSession, invitation: EmployeeInvitation) -> None:
    await db.delete(invitation)
    await db.commit()
    log_info(logger, "crud.employee_invitations.delete", invitation_id=invitation.id, company_id=invitation.company_id, email=invitation.email)
