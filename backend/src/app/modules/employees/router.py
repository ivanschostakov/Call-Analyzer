from datetime import timedelta
import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from config import EMPLOYEE_INVITATION_LIFETIME_DAYS, ufa_now
from src.app.observability import log_exception, log_info
from src.app.modules.auth.dependencies import get_current_user
from src.app.modules.common import (
    OperationResponse,
    build_user_display_name,
    can_manage_company,
    conflict_exception,
    get_accessible_employee_or_404,
    get_existing_user_or_404,
    get_manageable_company_or_404,
    get_team_manageable_company_or_404,
    normalize_email_address,
)
from src.app.modules.employees.helpers import (
    accept_employee_invitation_for_user,
    build_employee_invitation_read,
    build_employee_read,
    validate_manager_assignment,
)
from src.app.services.email import send_company_invitation_email
from src.database import get_db
from src.database.crud import (
    clear_manager_for_company_employees,
    create_employee,
    create_employee_invitation,
    delete_employee,
    delete_employee_invitation,
    get_active_employee_invitation_by_company_id_and_email,
    get_employee_by_company_id_and_user_id,
    get_employee_invitation_by_id,
    get_user_by_email,
    list_employees_by_company_id_and_manager_user_id,
    list_employee_invitations_by_company_id,
    list_employees_by_company_id,
    update_user,
    update_employee,
)
from src.database.models import EmployeeInvitation, User
from src.database.schemas import (
    EmployeeCreate,
    EmployeeInvitationAccept,
    EmployeeInvitationCreate,
    EmployeeInvitationRead,
    EmployeeRead,
    EmployeeUpdate,
    UserUpdate,
)
from src.enums import UserRole

employees_router = APIRouter(prefix="/employees", tags=["employees"])
logger = logging.getLogger(__name__)


@employees_router.get("", response_model=list[EmployeeRead])
async def list_employees_route(company_id: int = Query(...), current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> list[EmployeeRead]:
    log_info(logger, "employees.list.start", actor_user_id=current_user.id, company_id=company_id)
    company = await get_team_manageable_company_or_404(db, current_user, company_id)
    if can_manage_company(current_user, company): items = await list_employees_by_company_id(db, company_id)
    else:
        items = await list_employees_by_company_id_and_manager_user_id(db, company_id, current_user.id)
        self_membership = await get_employee_by_company_id_and_user_id(db, company_id, current_user.id)
        if self_membership is not None: items = [self_membership, *items]

        unique_items: dict[int, object] = {}
        for item in items: unique_items[item.id] = item
        items = list(unique_items.values())
    log_info(logger, "employees.list.success", actor_user_id=current_user.id, company_id=company_id, count=len(items))
    return [build_employee_read(item) for item in items]


@employees_router.get("/invitations", response_model=list[EmployeeInvitationRead])
async def list_employee_invitations_route(company_id: int = Query(...), current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> list[EmployeeInvitationRead]:
    log_info(logger, "employees.invitations.list.start", actor_user_id=current_user.id, company_id=company_id)
    await get_manageable_company_or_404(db, current_user, company_id)
    items = await list_employee_invitations_by_company_id(db, company_id)
    log_info(logger, "employees.invitations.list.success", actor_user_id=current_user.id, company_id=company_id, count=len(items))
    return [build_employee_invitation_read(item) for item in items]


@employees_router.post("/invitations", response_model=EmployeeInvitationRead, status_code=status.HTTP_201_CREATED)
async def create_employee_invitation_route(payload: EmployeeInvitationCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> EmployeeInvitationRead:
    log_info(logger, "employees.invitations.create.start", actor_user_id=current_user.id, payload=payload.model_dump())
    company = await get_manageable_company_or_404(db, current_user, payload.company_id)
    normalized_email = normalize_email_address(str(payload.email))

    existing_user = await get_user_by_email(db, normalized_email)
    if existing_user is not None:
        if existing_user.id == company.owner_id: raise conflict_exception("Company owner already has access.")

        existing_membership = await get_employee_by_company_id_and_user_id(db, company.id, existing_user.id)
        if existing_membership is not None: raise conflict_exception("Employee already exists for this company.")

    existing_invitation = await get_active_employee_invitation_by_company_id_and_email(db, company.id, normalized_email)
    if existing_invitation is not None: raise conflict_exception("Invitation has already been sent to this email.")

    invitation = await create_employee_invitation(
        db,
        EmployeeInvitation(
            company_id=company.id,
            invited_by_user_id=current_user.id,
            email=normalized_email,
            token=uuid.uuid4().hex,
            expires_at=ufa_now() + timedelta(days=EMPLOYEE_INVITATION_LIFETIME_DAYS),
        ),
    )

    try:
        await send_company_invitation_email(
            recipient_email=normalized_email,
            company_name=company.name,
            invited_by_name=build_user_display_name(current_user) or current_user.email,
            token=invitation.token,
        )
    except Exception as exc:
        await delete_employee_invitation(db, invitation)
        log_exception(logger, "employees.invitations.create.failed", actor_user_id=current_user.id, company_id=company.id, email=normalized_email)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to send invitation email: {exc}") from exc

    saved_invitation = await get_employee_invitation_by_id(db, invitation.id)
    if saved_invitation is None: raise RuntimeError("Created invitation could not be reloaded.")
    log_info(logger, "employees.invitations.create.success", actor_user_id=current_user.id, company_id=company.id, invitation_id=saved_invitation.id, email=normalized_email)
    return build_employee_invitation_read(saved_invitation)


@employees_router.post("/invitations/accept", response_model=OperationResponse)
async def accept_employee_invitation_route(payload: EmployeeInvitationAccept, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> OperationResponse:
    log_info(logger, "employees.invitations.accept.start", actor_user_id=current_user.id, payload=payload.model_dump())
    invitation = await accept_employee_invitation_for_user(db, token=payload.token, user=current_user)
    log_info(logger, "employees.invitations.accept.success", actor_user_id=current_user.id, invitation_id=invitation.id, company_id=invitation.company_id)
    return OperationResponse(message=f"Invitation to company {invitation.company.name} accepted successfully.")


@employees_router.post("", response_model=EmployeeRead, status_code=status.HTTP_201_CREATED)
async def create_employee_route(payload: EmployeeCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> EmployeeRead:
    log_info(logger, "employees.create.start", actor_user_id=current_user.id, payload=payload.model_dump())
    await get_manageable_company_or_404(db, current_user, payload.company_id)
    await get_existing_user_or_404(db, payload.user_id)
    manager_user_id = await validate_manager_assignment(
        db,
        company_id=payload.company_id,
        employee_user_id=payload.user_id,
        manager_user_id=payload.manager_user_id,
    )
    try:
        employee = await create_employee(
            db,
            EmployeeCreate(
                user_id=payload.user_id,
                company_id=payload.company_id,
                manager_user_id=manager_user_id,
            ),
        )
    except IntegrityError as exc:
        log_exception(logger, "employees.create.conflict", actor_user_id=current_user.id, company_id=payload.company_id, user_id=payload.user_id)
        raise conflict_exception("Employee already exists for this company.") from exc
    employee = await get_accessible_employee_or_404(db, current_user, employee.id)
    log_info(logger, "employees.create.success", actor_user_id=current_user.id, employee_id=employee.id, company_id=employee.company_id, user_id=employee.user_id)
    return build_employee_read(employee)


@employees_router.get("/{employee_id}", response_model=EmployeeRead)
async def get_employee_route(employee_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> EmployeeRead:
    log_info(logger, "employees.get.start", actor_user_id=current_user.id, employee_id=employee_id)
    employee = await get_accessible_employee_or_404(db, current_user, employee_id)
    log_info(logger, "employees.get.success", actor_user_id=current_user.id, employee_id=employee.id, company_id=employee.company_id)
    return build_employee_read(employee)


@employees_router.patch("/{employee_id}", response_model=EmployeeRead)
async def update_employee_route(employee_id: int, payload: EmployeeUpdate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> EmployeeRead:
    log_info(logger, "employees.update.start", actor_user_id=current_user.id, employee_id=employee_id, changes=payload.model_dump(exclude_unset=True))
    employee = await get_accessible_employee_or_404(db, current_user, employee_id)
    await get_manageable_company_or_404(db, current_user, employee.company_id)
    if payload.company_id is not None: await get_manageable_company_or_404(db, current_user, payload.company_id)
    if payload.user_id is not None: await get_existing_user_or_404(db, payload.user_id)

    next_user_id = payload.user_id if payload.user_id is not None else employee.user_id
    next_company_id = payload.company_id if payload.company_id is not None else employee.company_id
    next_role = payload.user_role if payload.user_role is not None else (employee.user.role if employee.user else UserRole.EMPLOYEE)
    next_manager_user_id = payload.manager_user_id if "manager_user_id" in payload.model_fields_set else employee.manager_user_id

    if next_role == UserRole.OWNER: raise conflict_exception("Employee membership cannot be promoted to owner.")
    if next_role == UserRole.ADMIN: next_manager_user_id = None
    else:
        next_manager_user_id = await validate_manager_assignment(
            db,
            company_id=next_company_id,
            employee_user_id=next_user_id,
            manager_user_id=next_manager_user_id,
        )

    update_data: dict[str, int | None] = {}
    if "user_id" in payload.model_fields_set: update_data["user_id"] = payload.user_id
    if "company_id" in payload.model_fields_set: update_data["company_id"] = payload.company_id
    if "manager_user_id" in payload.model_fields_set or payload.user_role is not None: update_data["manager_user_id"] = next_manager_user_id

    try:
        employee = await update_employee(
            db,
            employee,
            EmployeeUpdate(**update_data),
        )
    except IntegrityError as exc:
        error_text = str(getattr(exc, "orig", exc)).lower()
        if "uq_employees_user_company" in error_text or "duplicate key" in error_text:
            log_exception(logger, "employees.update.conflict", actor_user_id=current_user.id, employee_id=employee_id)
            raise conflict_exception("Employee already exists for this company.") from exc
        log_exception(logger, "employees.update.failed", actor_user_id=current_user.id, employee_id=employee_id)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to update employee.") from exc

    target_user = employee.user if employee.user and employee.user.id == next_user_id else await get_existing_user_or_404(db, next_user_id)
    previous_role = target_user.role
    if payload.user_role is not None and previous_role != next_role: await update_user(db, target_user, UserUpdate(role=next_role))

    if previous_role == UserRole.ADMIN and next_role != UserRole.ADMIN: await clear_manager_for_company_employees(db, employee.company_id, employee.user_id)

    employee = await get_accessible_employee_or_404(db, current_user, employee.id)
    log_info(logger, "employees.update.success", actor_user_id=current_user.id, employee_id=employee.id, company_id=employee.company_id, user_id=employee.user_id)
    return build_employee_read(employee)


@employees_router.delete("/{employee_id}", response_model=OperationResponse)
async def delete_employee_route(employee_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> OperationResponse:
    log_info(logger, "employees.delete.start", actor_user_id=current_user.id, employee_id=employee_id)
    employee = await get_accessible_employee_or_404(db, current_user, employee_id)
    await get_manageable_company_or_404(db, current_user, employee.company_id)
    if employee.user and employee.user.role == UserRole.ADMIN: await clear_manager_for_company_employees(db, employee.company_id, employee.user_id)
    await delete_employee(db, employee)
    log_info(logger, "employees.delete.success", actor_user_id=current_user.id, employee_id=employee.id, company_id=employee.company_id, user_id=employee.user_id)
    return OperationResponse(message="Employee deleted successfully.")
