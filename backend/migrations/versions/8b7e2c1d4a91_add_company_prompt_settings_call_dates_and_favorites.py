"""add company prompt settings call dates and favorites

Revision ID: 8b7e2c1d4a91
Revises: f3a8c91d2b44
Create Date: 2026-04-06 17:10:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "8b7e2c1d4a91"
down_revision: str | Sequence[str] | None = "f3a8c91d2b44"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("companies", sa.Column("transcription_hint_prompt", sa.Text(), nullable=True))
    op.add_column(
        "companies",
        sa.Column(
            "report_summary_questions",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'::json"),
        ),
    )

    op.add_column("transcriptions", sa.Column("call_started_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f("ix_transcriptions_call_started_at"), "transcriptions", ["call_started_at"], unique=False)

    op.create_table(
        "transcription_favorites",
        sa.Column("transcription_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.ForeignKeyConstraint(["transcription_id"], ["transcriptions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("transcription_id", "user_id", name="uq_transcription_favorites_transcription_user"),
    )
    op.create_index(op.f("ix_transcription_favorites_id"), "transcription_favorites", ["id"], unique=False)
    op.create_index(op.f("ix_transcription_favorites_transcription_id"), "transcription_favorites", ["transcription_id"], unique=False)
    op.create_index(op.f("ix_transcription_favorites_user_id"), "transcription_favorites", ["user_id"], unique=False)

    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            update transcriptions
            set call_started_at = created_at
            where call_started_at is null
            """
        )
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_transcription_favorites_user_id"), table_name="transcription_favorites")
    op.drop_index(op.f("ix_transcription_favorites_transcription_id"), table_name="transcription_favorites")
    op.drop_index(op.f("ix_transcription_favorites_id"), table_name="transcription_favorites")
    op.drop_table("transcription_favorites")

    op.drop_index(op.f("ix_transcriptions_call_started_at"), table_name="transcriptions")
    op.drop_column("transcriptions", "call_started_at")

    op.drop_column("companies", "report_summary_questions")
    op.drop_column("companies", "transcription_hint_prompt")
