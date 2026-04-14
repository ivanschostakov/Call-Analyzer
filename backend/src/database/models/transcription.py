from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.database.limits import FILE_ID_MAX_LENGTH, FILE_PATH_MAX_LENGTH, TRANSCRIPTION_STATUS_MAX_LENGTH
from src.database.mixins import IdPkMixin, TimestampMixin, UfaDateTime
from src.enums import TranscriptionStatus


class Transcription(Base, IdPkMixin, TimestampMixin):
    __tablename__ = "transcriptions"
    __table_args__ = (
        UniqueConstraint("company_id", "file_id", name="uq_transcriptions_company_file"),
    )

    company_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    uploaded_by_user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    detected_employee_user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    file_id: Mapped[str] = mapped_column(String(length=FILE_ID_MAX_LENGTH), nullable=False, index=True)
    original_filename: Mapped[str] = mapped_column(String(length=255), nullable=False)
    source_path: Mapped[str] = mapped_column(String(length=FILE_PATH_MAX_LENGTH), nullable=False)
    file_path: Mapped[str] = mapped_column(String(length=FILE_PATH_MAX_LENGTH), nullable=False)

    status: Mapped[str] = mapped_column(
        String(length=TRANSCRIPTION_STATUS_MAX_LENGTH),
        nullable=False,
        default=TranscriptionStatus.UPLOADED.value,
        server_default=TranscriptionStatus.UPLOADED.value,
    )
    language: Mapped[str | None] = mapped_column(String(length=32), nullable=True)
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    segments: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    call_started_at: Mapped[datetime | None] = mapped_column(UfaDateTime(), nullable=True, index=True)
    transcribed_at: Mapped[datetime | None] = mapped_column(UfaDateTime(), nullable=True)

    company: Mapped["Company"] = relationship(back_populates="transcriptions")
    uploaded_by: Mapped["User"] = relationship(back_populates="transcriptions_uploaded", foreign_keys=[uploaded_by_user_id])
    detected_employee_user: Mapped["User | None"] = relationship(back_populates="detected_transcriptions", foreign_keys=[detected_employee_user_id])
    analyses: Mapped[list["Analysis"]] = relationship(back_populates="transcription")
    favorites: Mapped[list["TranscriptionFavorite"]] = relationship(back_populates="transcription", cascade="all, delete-orphan")
