from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.database.limits import EMAIL_MAX_LENGTH
from src.database.mixins import IdPkMixin, TimestampMixin, UfaDateTime


class EmployeeInvitation(Base, IdPkMixin, TimestampMixin):
    __tablename__ = "employee_invitations"

    company_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    invited_by_user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    accepted_by_user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    email: Mapped[str] = mapped_column(String(length=EMAIL_MAX_LENGTH), nullable=False, index=True)
    token: Mapped[str] = mapped_column(String(length=64), nullable=False, unique=True, index=True)
    accepted_at: Mapped[datetime | None] = mapped_column(UfaDateTime(), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(UfaDateTime(), nullable=False, index=True)

    company: Mapped["Company"] = relationship(back_populates="employee_invitations")
    invited_by: Mapped["User | None"] = relationship(foreign_keys=[invited_by_user_id], back_populates="employee_invitations_sent")
    accepted_by: Mapped["User | None"] = relationship(foreign_keys=[accepted_by_user_id], back_populates="employee_invitations_accepted")
