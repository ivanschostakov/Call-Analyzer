from sqlalchemy import BigInteger, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.database.mixins import IdPkMixin, TimestampMixin


class TranscriptionFavorite(Base, IdPkMixin, TimestampMixin):
    __tablename__ = "transcription_favorites"
    __table_args__ = (
        UniqueConstraint("transcription_id", "user_id", name="uq_transcription_favorites_transcription_user"),
    )

    transcription_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("transcriptions.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    transcription: Mapped["Transcription"] = relationship(back_populates="favorites")
    user: Mapped["User"] = relationship(back_populates="favorite_transcriptions")
