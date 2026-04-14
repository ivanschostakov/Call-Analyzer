from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.database.limits import TEMPLATE_NAME_MAX_LENGTH
from src.database.mixins import IdPkMixin, TimestampMixin


class Analysis(Base, IdPkMixin, TimestampMixin):
    __tablename__ = "analyses"
    __table_args__ = (
        UniqueConstraint("transcription_id", "template_id", "active_key", name="uq_analyses_transcription_template_active"),
    )

    company_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    created_by_user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    transcription_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("transcriptions.id", ondelete="SET NULL"), nullable=True, index=True)
    template_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("templates.id", ondelete="SET NULL"), nullable=True, index=True)

    template_name: Mapped[str] = mapped_column(String(length=TEMPLATE_NAME_MAX_LENGTH), nullable=False)
    instructions: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"), index=True)
    active_key: Mapped[int | None] = mapped_column(Integer, nullable=True, default=1)

    company: Mapped["Company"] = relationship(back_populates="analyses")
    created_by: Mapped["User | None"] = relationship(back_populates="analyses_created")
    transcription: Mapped["Transcription | None"] = relationship(back_populates="analyses")
    template: Mapped["Template | None"] = relationship(back_populates="analyses")
    results: Mapped[list["AnalysisResult"]] = relationship(
        back_populates="analysis",
        cascade="all, delete-orphan",
        order_by="AnalysisResult.position.asc(), AnalysisResult.id.asc()",
    )

    @property
    def criteria_evaluated(self) -> list["AnalysisResult"]:
        return self.results
