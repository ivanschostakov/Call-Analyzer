import logging as py_logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.observability import log_info
from src.database.models import User
from src.database.schemas import UserCreate, UserUpdate

logger = py_logging.getLogger(__name__)


async def create_user(db: AsyncSession, payload: UserCreate) -> User:
    log_info(logger, "crud.users.create.start", payload=payload.model_dump())
    data = payload.model_dump()
    data["email"] = data["email"].lower().strip()
    user = User(**data)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    log_info(logger, "crud.users.create.success", user_id=user.id, email=user.email, role=user.role)
    return user


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    user = await db.get(User, user_id)
    log_info(logger, "crud.users.get_by_id", user_id=user_id, found=bool(user))
    return user
async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    statement = select(User).where(func.lower(User.email) == email.lower().strip())
    user = (await db.execute(statement)).scalar_one_or_none()
    log_info(logger, "crud.users.get_by_email", email=email, found=bool(user))
    return user


async def list_users(db: AsyncSession) -> list[User]:
    statement = select(User).order_by(User.created_at.desc())
    items = list((await db.execute(statement)).scalars().all())
    log_info(logger, "crud.users.list", count=len(items))
    return items


async def update_user(db: AsyncSession, user: User, payload: UserUpdate) -> User:
    updates = payload.model_dump(exclude_unset=True)
    log_info(logger, "crud.users.update.start", user_id=user.id, changes=updates)
    if "email" in updates and updates["email"] is not None: updates["email"] = updates["email"].lower().strip()
    for field, value in updates.items(): setattr(user, field, value)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    log_info(logger, "crud.users.update.success", user_id=user.id, email=user.email)
    return user


async def delete_user(db: AsyncSession, user: User) -> None:
    await db.delete(user)
    await db.commit()
    log_info(logger, "crud.users.delete", user_id=user.id, email=user.email)
