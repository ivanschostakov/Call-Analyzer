from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.database.mixins import IdPkMixin, TimestampMixin, UfaDateTime


class PasswordResetRequest(Base, IdPkMixin, TimestampMixin):
    __tablename__ = "password_reset_requests"

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(
        String(length=64),
        nullable=False,
        unique=True,
        index=True,
    )
    expires_at: Mapped[datetime] = mapped_column(
        UfaDateTime(),
        nullable=False,
        index=True,
    )
    used_at: Mapped[datetime | None] = mapped_column(UfaDateTime(), nullable=True)

    user: Mapped["User"] = relationship(back_populates="password_reset_requests")
