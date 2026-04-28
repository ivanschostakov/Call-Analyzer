import logging

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config import ufa_now
from src.app.observability import log_info
from src.database.models import MentorMessage, MentorThread
from src.database.schemas import MentorMessageCreate, MentorThreadCreate, MentorThreadUpdate

logger = logging.getLogger(__name__)


async def create_mentor_thread(db: AsyncSession, payload: MentorThreadCreate) -> MentorThread:
    thread = MentorThread(
        owner_user_id=payload.owner_user_id,
        company_id=payload.company_id,
        template_id=payload.template_id,
        openai_conversation_id=payload.openai_conversation_id,
        title=payload.title,
    )
    db.add(thread)
    await db.commit()
    await db.refresh(thread)
    log_info(logger, "crud.mentor.thread.create", thread_id=thread.id, company_id=thread.company_id, owner_user_id=thread.owner_user_id)
    return thread


async def update_mentor_thread(db: AsyncSession, thread: MentorThread, payload: MentorThreadUpdate) -> MentorThread:
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(thread, field, value)
    await db.commit()
    await db.refresh(thread)
    log_info(logger, "crud.mentor.thread.update", thread_id=thread.id, changes=list(changes))
    return thread


async def get_mentor_thread_by_id_and_owner_user_id(
    db: AsyncSession,
    thread_id: int,
    owner_user_id: int,
    *,
    load_messages: bool = False,
) -> MentorThread | None:
    statement = select(MentorThread).where(MentorThread.id == thread_id, MentorThread.owner_user_id == owner_user_id)
    if load_messages:
        statement = statement.options(selectinload(MentorThread.messages))
    thread = (await db.execute(statement)).scalar_one_or_none()
    log_info(logger, "crud.mentor.thread.get_by_owner", thread_id=thread_id, owner_user_id=owner_user_id, found=bool(thread))
    return thread


async def list_mentor_threads_by_company_and_owner_user_id(
    db: AsyncSession,
    company_id: int,
    owner_user_id: int,
) -> list[MentorThread]:
    statement = (
        select(MentorThread)
        .where(MentorThread.company_id == company_id, MentorThread.owner_user_id == owner_user_id)
        .order_by(MentorThread.updated_at.desc(), MentorThread.id.desc())
    )
    items = list((await db.execute(statement)).scalars().all())
    log_info(logger, "crud.mentor.thread.list", company_id=company_id, owner_user_id=owner_user_id, count=len(items))
    return items


async def create_mentor_message(db: AsyncSession, payload: MentorMessageCreate) -> MentorMessage:
    message = MentorMessage(
        thread_id=payload.thread_id,
        role=payload.role,
        content=payload.content,
        analysis_ids=list(payload.analysis_ids),
        selected_columns=list(payload.selected_columns),
        row_count=payload.row_count,
        summarized_row_count=payload.summarized_row_count,
        omitted_row_count=payload.omitted_row_count,
    )
    db.add(message)
    await db.execute(update(MentorThread).where(MentorThread.id == payload.thread_id).values(updated_at=ufa_now()))
    await db.commit()
    await db.refresh(message)
    log_info(logger, "crud.mentor.message.create", message_id=message.id, thread_id=message.thread_id, role=message.role)
    return message


async def list_mentor_messages_by_thread_id(db: AsyncSession, thread_id: int) -> list[MentorMessage]:
    statement = (
        select(MentorMessage)
        .where(MentorMessage.thread_id == thread_id)
        .order_by(MentorMessage.created_at.asc(), MentorMessage.id.asc())
    )
    items = list((await db.execute(statement)).scalars().all())
    log_info(logger, "crud.mentor.message.list", thread_id=thread_id, count=len(items))
    return items
