import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from src.app.modules.analysis.helpers import (
    build_report_summary_rows,
    resolve_report_summary_columns,
    resolve_report_summary_template,
)
from src.app.modules.auth.dependencies import get_current_user
from src.app.modules.common import (
    get_accessible_company_or_404,
    get_visible_user_ids_for_company,
    is_analysis_visible_to_user_ids,
)
from src.app.modules.mentor.schemas import (
    MentorMessageCreatePayload,
    MentorMessageResponse,
    MentorReplyResponse,
    MentorThreadDetailResponse,
    MentorThreadResponse,
)
from src.app.observability import log_exception, log_info
from src.app.services.mentor import MentorContext, mentor_service
from src.database import get_db
from src.database.crud import (
    create_mentor_message,
    create_mentor_thread,
    get_mentor_thread_by_id_and_owner_user_id,
    list_analyses_by_ids,
    list_criteria_by_template_id,
    list_mentor_messages_by_thread_id,
    list_mentor_threads_by_company_and_owner_user_id,
    update_mentor_thread,
)
from src.database.models import MentorMessage, MentorThread, User
from src.database.schemas import CriterionRead, MentorMessageCreate, MentorThreadCreate, MentorThreadUpdate

mentor_router = APIRouter(prefix="/mentor", tags=["mentor"])
logger = logging.getLogger(__name__)


def build_thread_title(prompt: str) -> str:
    normalized = " ".join(prompt.strip().split())
    if len(normalized) <= 80:
        return normalized or "Новый диалог"
    return f"{normalized[:77].rstrip()}..."


def build_mentor_thread_response(thread: MentorThread) -> MentorThreadResponse:
    return MentorThreadResponse(
        id=thread.id,
        owner_user_id=thread.owner_user_id,
        company_id=thread.company_id,
        template_id=thread.template_id,
        title=thread.title,
        created_at=thread.created_at,
        updated_at=thread.updated_at,
    )


def build_mentor_message_response(message: MentorMessage) -> MentorMessageResponse:
    return MentorMessageResponse(
        id=message.id,
        thread_id=message.thread_id,
        role=message.role,
        content=message.content,
        analysis_ids=list(message.analysis_ids or []),
        selected_columns=list(message.selected_columns or []),
        row_count=message.row_count,
        summarized_row_count=message.summarized_row_count,
        omitted_row_count=message.omitted_row_count,
        created_at=message.created_at,
        updated_at=message.updated_at,
    )


@mentor_router.get("/threads", response_model=list[MentorThreadResponse])
async def list_mentor_threads_route(
    company_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[MentorThreadResponse]:
    log_info(logger, "mentor.thread.list.start", actor_user_id=current_user.id, company_id=company_id)
    await get_accessible_company_or_404(db, current_user, company_id)
    threads = await list_mentor_threads_by_company_and_owner_user_id(db, company_id, current_user.id)
    log_info(logger, "mentor.thread.list.success", actor_user_id=current_user.id, company_id=company_id, count=len(threads))
    return [build_mentor_thread_response(thread) for thread in threads]


@mentor_router.get("/threads/{thread_id}", response_model=MentorThreadDetailResponse)
async def get_mentor_thread_route(
    thread_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MentorThreadDetailResponse:
    log_info(logger, "mentor.thread.get.start", actor_user_id=current_user.id, thread_id=thread_id)
    thread = await get_mentor_thread_by_id_and_owner_user_id(db, thread_id, current_user.id)
    if thread is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mentor thread not found.")
    await get_accessible_company_or_404(db, current_user, thread.company_id)
    messages = await list_mentor_messages_by_thread_id(db, thread.id)
    log_info(logger, "mentor.thread.get.success", actor_user_id=current_user.id, thread_id=thread_id, message_count=len(messages))
    return MentorThreadDetailResponse(
        **build_mentor_thread_response(thread).model_dump(),
        messages=[build_mentor_message_response(message) for message in messages],
    )


async def build_mentor_context(
    *,
    db: AsyncSession,
    current_user: User,
    payload: MentorMessageCreatePayload,
) -> tuple[MentorContext, list[str], int, int, list[str]]:
    company = await get_accessible_company_or_404(db, current_user, payload.company_id)
    template = await resolve_report_summary_template(db, current_user, payload.company_id, payload.template_id)
    visible_user_ids = await get_visible_user_ids_for_company(db, current_user, company)
    analyses = await list_analyses_by_ids(db, payload.analysis_ids)
    analysis_by_id = {analysis.id: analysis for analysis in analyses}
    missing_ids = [analysis_id for analysis_id in payload.analysis_ids if analysis_id not in analysis_by_id]
    if missing_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Some selected mentor rows were not found.")

    ordered_analyses = [analysis_by_id[analysis_id] for analysis_id in payload.analysis_ids]
    for analysis in ordered_analyses:
        if analysis.company_id != payload.company_id or analysis.template_id != payload.template_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="All selected mentor rows must belong to the same report.")
        if not is_analysis_visible_to_user_ids(analysis, visible_user_ids):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Some selected mentor rows are not accessible.")

    criteria_models = await list_criteria_by_template_id(db, template.id)
    criteria = [CriterionRead.model_validate(item) for item in criteria_models]
    selected_columns = resolve_report_summary_columns(criteria, payload.columns)
    rows = build_report_summary_rows(ordered_analyses, selected_columns)
    if not rows:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="There are no selected mentor rows.")

    selected_column_keys = [column.key for column in selected_columns]
    vector_store_ids = [company.vector_store_id] if company.vector_store_id else []
    return (
        MentorContext(
            template_name=template.name,
            user_prompt=payload.prompt,
            columns=selected_columns,
            rows=rows,
        ),
        vector_store_ids,
        len(rows),
        payload.template_id,
        selected_column_keys,
    )


@mentor_router.post("/messages", response_model=MentorReplyResponse, status_code=status.HTTP_201_CREATED)
async def create_mentor_message_route(
    payload: MentorMessageCreatePayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MentorReplyResponse:
    log_info(
        logger,
        "mentor.message.create.start",
        actor_user_id=current_user.id,
        thread_id=payload.thread_id,
        company_id=payload.company_id,
        template_id=payload.template_id,
        analysis_count=len(payload.analysis_ids),
        selected_column_count=len(payload.columns or []),
        prompt_characters=len(payload.prompt.strip()),
    )
    context, vector_store_ids, row_count, template_id, selected_column_keys = await build_mentor_context(
        db=db,
        current_user=current_user,
        payload=payload,
    )

    thread: MentorThread | None = None
    conversation_id: str | None = None
    if payload.thread_id is not None:
        thread = await get_mentor_thread_by_id_and_owner_user_id(db, payload.thread_id, current_user.id)
        if thread is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mentor thread not found.")
        if thread.company_id != payload.company_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mentor thread belongs to another company.")
        conversation_id = thread.openai_conversation_id

    try:
        mentor_response = await mentor_service.send_message(
            conversation_id=conversation_id,
            user_id=current_user.id,
            context=context,
            vector_store_ids=vector_store_ids,
        )
    except HTTPException:
        raise
    except Exception as exc:
        log_exception(
            logger,
            "mentor.message.create.failed",
            actor_user_id=current_user.id,
            thread_id=payload.thread_id,
            company_id=payload.company_id,
            template_id=payload.template_id,
            detail=str(exc),
        )
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Mentor response failed: {exc}") from exc

    if thread is None:
        thread = await create_mentor_thread(
            db,
            MentorThreadCreate(
                owner_user_id=current_user.id,
                company_id=payload.company_id,
                template_id=template_id,
                openai_conversation_id=mentor_response.conversation_id,
                title=build_thread_title(payload.prompt),
            ),
        )
    else:
        update_payload = MentorThreadUpdate(
            template_id=template_id,
            openai_conversation_id=mentor_response.conversation_id,
        )
        if thread.openai_conversation_id != mentor_response.conversation_id or thread.template_id != template_id:
            thread = await update_mentor_thread(db, thread, update_payload)

    common_message_fields = {
        "thread_id": thread.id,
        "analysis_ids": payload.analysis_ids,
        "selected_columns": selected_column_keys,
        "row_count": row_count,
        "summarized_row_count": mentor_response.summarized_row_count,
        "omitted_row_count": mentor_response.omitted_row_count,
    }
    user_message = await create_mentor_message(
        db,
        MentorMessageCreate(
            **common_message_fields,
            role="user",
            content=payload.prompt.strip(),
        ),
    )
    assistant_message = await create_mentor_message(
        db,
        MentorMessageCreate(
            **common_message_fields,
            role="assistant",
            content=mentor_response.text,
        ),
    )

    log_info(
        logger,
        "mentor.message.create.success",
        actor_user_id=current_user.id,
        thread_id=thread.id,
        company_id=payload.company_id,
        template_id=payload.template_id,
        conversation_reset_reason=mentor_response.conversation_reset_reason,
    )
    return MentorReplyResponse(
        thread=build_mentor_thread_response(thread),
        user_message=build_mentor_message_response(user_message),
        assistant_message=build_mentor_message_response(assistant_message),
    )
