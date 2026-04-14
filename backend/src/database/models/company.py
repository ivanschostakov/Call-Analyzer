from datetime import date, datetime

from sqlalchemy import JSON, BigInteger, Boolean, Date, ForeignKey, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.database.limits import COMPANY_NAME_MAX_LENGTH, VECTOR_STORE_ID_MAX_LENGTH
from src.database.mixins import IdPkMixin, TimestampMixin, UfaDateTime


class Company(Base, IdPkMixin, TimestampMixin):
    __tablename__ = "companies"
    __table_args__ = (
        UniqueConstraint("owner_id", "name", name="uq_companies_owner_name"),
    )

    owner_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(length=COMPANY_NAME_MAX_LENGTH), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    transcription_hint_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_summary_questions: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    vector_store_id: Mapped[str | None] = mapped_column(String(length=VECTOR_STORE_ID_MAX_LENGTH), nullable=True)
    beeline_api_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    beeline_auto_export_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    beeline_auto_analysis_template_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("templates.id", ondelete="SET NULL"), nullable=True, index=True)
    beeline_last_sync_target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    beeline_last_sync_started_at: Mapped[datetime | None] = mapped_column(UfaDateTime(), nullable=True)
    beeline_last_sync_finished_at: Mapped[datetime | None] = mapped_column(UfaDateTime(), nullable=True)
    beeline_last_sync_status: Mapped[str | None] = mapped_column(String(length=32), nullable=True)
    beeline_last_sync_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    beeline_last_auto_sync_target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    beeline_last_auto_sync_started_at: Mapped[datetime | None] = mapped_column(UfaDateTime(), nullable=True)
    beeline_last_auto_sync_finished_at: Mapped[datetime | None] = mapped_column(UfaDateTime(), nullable=True)
    beeline_last_auto_sync_status: Mapped[str | None] = mapped_column(String(length=32), nullable=True)
    beeline_last_auto_sync_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    owner: Mapped["User"] = relationship(back_populates="companies_owned", foreign_keys=[owner_id])
    employees: Mapped[list["Employee"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    employee_invitations: Mapped[list["EmployeeInvitation"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    templates: Mapped[list["Template"]] = relationship(
        back_populates="company",
        cascade="all, delete-orphan",
        foreign_keys="Template.company_id",
    )
    transcriptions: Mapped[list["Transcription"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    analyses: Mapped[list["Analysis"]] = relationship(back_populates="company", cascade="all, delete-orphan")
