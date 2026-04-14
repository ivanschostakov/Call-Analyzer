from sqlalchemy import BigInteger, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.database.mixins import IdPkMixin, TimestampMixin


class Employee(Base, IdPkMixin, TimestampMixin):
    __tablename__ = "employees"
    __table_args__ = (
        UniqueConstraint("user_id", "company_id", name="uq_employees_user_company"),
    )

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    company_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    manager_user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    user: Mapped["User"] = relationship(back_populates="employee_memberships", foreign_keys=[user_id])
    company: Mapped["Company"] = relationship(back_populates="employees")
    manager: Mapped["User | None"] = relationship(back_populates="managed_employee_memberships", foreign_keys=[manager_user_id])
