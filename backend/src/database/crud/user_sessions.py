import logging as py_logging

from sqlalchemy.ext.asyncio import AsyncSession

from src.app.observability import log_info
from src.database.models import UserSession
from src.database.schemas import UserSessionCreate, UserSessionUpdate

logger = py_logging.getLogger(__name__)


async def create_user_session(db: AsyncSession, payload: UserSessionCreate) -> UserSession:
    log_info(logger, "crud.user_sessions.create.start", payload=payload.model_dump(exclude_none=True))
    session = UserSession(**payload.model_dump(exclude_none=True))
    db.add(session)
    await db.commit()
    await db.refresh(session)
    log_info(logger, "crud.user_sessions.create.success", session_id=session.id, user_id=session.user_id)
    return session


async def get_user_session_by_id(db: AsyncSession, session_id: int) -> UserSession | None:
    session = await db.get(UserSession, session_id)
    log_info(logger, "crud.user_sessions.get_by_id", session_id=session_id, found=bool(session))
    return session


async def list_user_sessions_by_user_id(db: AsyncSession, user_id: int) -> list[UserSession]:
    from sqlalchemy import select

    statement = select(UserSession).where(UserSession.user_id == user_id).order_by(UserSession.created_at.desc())
    items = list((await db.execute(statement)).scalars().all())
    log_info(logger, "crud.user_sessions.list_by_user", user_id=user_id, count=len(items))
    return items


async def update_user_session(db: AsyncSession, user_session: UserSession, payload: UserSessionUpdate) -> UserSession:
    changes = payload.model_dump(exclude_unset=True)
    log_info(logger, "crud.user_sessions.update.start", session_id=user_session.id, changes=changes)
    for field, value in changes.items():
        setattr(user_session, field, value)

    db.add(user_session)
    await db.commit()
    await db.refresh(user_session)
    log_info(logger, "crud.user_sessions.update.success", session_id=user_session.id, user_id=user_session.user_id)
    return user_session


async def delete_user_session(db: AsyncSession, user_session: UserSession) -> None:
    await db.delete(user_session)
    await db.commit()
    log_info(logger, "crud.user_sessions.delete", session_id=user_session.id, user_id=user_session.user_id)
