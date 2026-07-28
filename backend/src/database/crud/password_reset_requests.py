import logging
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.observability import log_info
from src.database.models import PasswordResetRequest

logger = logging.getLogger(__name__)


async def replace_password_reset_request(
    db: AsyncSession,
    *,
    user_id: int,
    token_hash: str,
    expires_at: datetime,
) -> PasswordResetRequest:
    await db.execute(
        delete(PasswordResetRequest).where(
            PasswordResetRequest.user_id == user_id,
            PasswordResetRequest.used_at.is_(None),
        )
    )
    request = PasswordResetRequest(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    db.add(request)
    await db.commit()
    await db.refresh(request)
    log_info(
        logger,
        "crud.password_reset.replace",
        request_id=request.id,
        user_id=user_id,
        expires_at=expires_at.isoformat(),
    )
    return request


async def get_password_reset_request_by_token_hash(
    db: AsyncSession,
    token_hash: str,
) -> PasswordResetRequest | None:
    statement = select(PasswordResetRequest).where(
        PasswordResetRequest.token_hash == token_hash,
    )
    request = (await db.execute(statement)).scalar_one_or_none()
    log_info(
        logger,
        "crud.password_reset.get_by_token_hash",
        found=request is not None,
    )
    return request
