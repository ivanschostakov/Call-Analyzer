from typing import Any

from sqlalchemy import JSON, BigInteger, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.database.mixins import IdPkMixin, TimestampMixin


class MentorMessage(Base, IdPkMixin, TimestampMixin):
    __tablename__ = "mentor_messages"

    thread_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("mentor_threads.id", ondelete="CASCADE"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(length=16), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    analysis_ids: Mapped[list[int]] = mapped_column(JSON, nullable=False, default=list)
    selected_columns: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    summarized_row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    omitted_row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    thread: Mapped["MentorThread"] = relationship(back_populates="messages")
