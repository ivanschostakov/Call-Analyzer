from sqlalchemy import BigInteger, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.database.mixins import IdPkMixin, TimestampMixin


class MentorThread(Base, IdPkMixin, TimestampMixin):
    __tablename__ = "mentor_threads"

    owner_user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    company_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    template_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("templates.id", ondelete="SET NULL"), nullable=True, index=True)
    openai_conversation_id: Mapped[str | None] = mapped_column(String(length=255), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(length=255), nullable=False)

    owner: Mapped["User"] = relationship(foreign_keys=[owner_user_id])
    company: Mapped["Company"] = relationship(foreign_keys=[company_id])
    template: Mapped["Template | None"] = relationship(foreign_keys=[template_id])
    messages: Mapped[list["MentorMessage"]] = relationship(
        back_populates="thread",
        cascade="all, delete-orphan",
        order_by="MentorMessage.created_at.asc(), MentorMessage.id.asc()",
    )
