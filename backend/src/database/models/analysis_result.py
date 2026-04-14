from sqlalchemy import JSON, BigInteger, Boolean, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.database.limits import CRITERION_NAME_MAX_LENGTH
from src.database.mixins import IdPkMixin, TimestampMixin
from src.enums import CriterionAnswerType, enum_values


class AnalysisResult(Base, IdPkMixin, TimestampMixin):
    __tablename__ = "analysis_results"
    __table_args__ = (
        UniqueConstraint("analysis_id", "criterion_id", name="uq_analysis_results_analysis_criterion"),
        UniqueConstraint("analysis_id", "position", name="uq_analysis_results_analysis_position"),
    )

    analysis_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    criterion_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("criteria.id", ondelete="SET NULL"), nullable=True, index=True)

    criterion_name: Mapped[str] = mapped_column(String(length=CRITERION_NAME_MAX_LENGTH), nullable=False)
    criterion_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    criterion_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    answer_type: Mapped[CriterionAnswerType] = mapped_column(
        Enum(CriterionAnswerType, name="criterion_answer_type", values_callable=enum_values),
        nullable=False,
    )
    answer_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    answer_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    answer_bool: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    evidence: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    analysis: Mapped["Analysis"] = relationship(back_populates="results")
    criterion: Mapped["Criterion | None"] = relationship(back_populates="analysis_results")

    @property
    def answer(self) -> str | int | bool | None:
        if self.answer_type == CriterionAnswerType.BOOLEAN:
            return self.answer_bool
        if self.answer_type == CriterionAnswerType.PERCENTAGE:
            return self.answer_number
        return self.answer_text
