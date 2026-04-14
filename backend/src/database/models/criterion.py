from sqlalchemy import BigInteger, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.enums import CriterionAnswerType, enum_values
from src.database.limits import CRITERION_NAME_MAX_LENGTH
from src.database.mixins import IdPkMixin, TimestampMixin


class Criterion(Base, IdPkMixin, TimestampMixin):
    __tablename__ = "criteria"
    __table_args__ = (
        UniqueConstraint("template_id", "name", name="uq_criteria_template_name"),
        UniqueConstraint("template_id", "position", name="uq_criteria_template_position"),
    )

    template_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("templates.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(length=CRITERION_NAME_MAX_LENGTH), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    answer_type: Mapped[CriterionAnswerType] = mapped_column(
        Enum(CriterionAnswerType, name="criterion_answer_type", values_callable=enum_values),
        nullable=False,
        default=CriterionAnswerType.TEXT,
        server_default=CriterionAnswerType.TEXT.value,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    template: Mapped["Template"] = relationship(back_populates="criteria")
    analysis_results: Mapped[list["AnalysisResult"]] = relationship(back_populates="criterion")
