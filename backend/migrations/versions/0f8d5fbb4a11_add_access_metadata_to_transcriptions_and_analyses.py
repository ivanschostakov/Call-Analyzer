"""add access metadata to transcriptions and analyses

Revision ID: 0f8d5fbb4a11
Revises: 39c624c04baf
Create Date: 2026-03-30 14:15:00.000000

"""
from pathlib import Path
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0f8d5fbb4a11"
down_revision: Union[str, Sequence[str], None] = "39c624c04baf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("transcriptions", sa.Column("uploaded_by_user_id", sa.BigInteger(), nullable=True))
    op.add_column("transcriptions", sa.Column("original_filename", sa.String(length=255), nullable=True))
    op.add_column("transcriptions", sa.Column("source_path", sa.String(length=1024), nullable=True))
    op.create_foreign_key(
        "fk_transcriptions_uploaded_by_user_id_users",
        "transcriptions",
        "users",
        ["uploaded_by_user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_transcriptions_uploaded_by_user_id", "transcriptions", ["uploaded_by_user_id"], unique=False)

    op.add_column("analyses", sa.Column("created_by_user_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        "fk_analyses_created_by_user_id_users",
        "analyses",
        "users",
        ["created_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_analyses_created_by_user_id", "analyses", ["created_by_user_id"], unique=False)

    bind = op.get_bind()
    transcriptions = sa.table(
        "transcriptions",
        sa.column("id", sa.BigInteger()),
        sa.column("company_id", sa.BigInteger()),
        sa.column("file_path", sa.String(length=1024)),
        sa.column("status", sa.String(length=32)),
        sa.column("uploaded_by_user_id", sa.BigInteger()),
        sa.column("original_filename", sa.String(length=255)),
        sa.column("source_path", sa.String(length=1024)),
    )
    companies = sa.table(
        "companies",
        sa.column("id", sa.BigInteger()),
        sa.column("owner_id", sa.BigInteger()),
    )
    analyses = sa.table(
        "analyses",
        sa.column("id", sa.BigInteger()),
        sa.column("company_id", sa.BigInteger()),
        sa.column("created_by_user_id", sa.BigInteger()),
    )

    transcription_rows = bind.execute(
        sa.select(
            transcriptions.c.id,
            transcriptions.c.file_path,
            companies.c.owner_id,
        ).select_from(
            transcriptions.join(companies, companies.c.id == transcriptions.c.company_id)
        )
    ).all()
    for transcription_id, file_path, owner_id in transcription_rows:
        bind.execute(
            transcriptions.update()
            .where(transcriptions.c.id == transcription_id)
            .values(
                uploaded_by_user_id=owner_id,
                original_filename=Path(file_path).name if file_path else f"{transcription_id}.wav",
                source_path=file_path,
            )
        )

    bind.execute(
        transcriptions.update()
        .where(transcriptions.c.status == "pending")
        .values(status="queued")
    )

    analysis_rows = bind.execute(
        sa.select(
            analyses.c.id,
            companies.c.owner_id,
        ).select_from(
            analyses.join(companies, companies.c.id == analyses.c.company_id)
        )
    ).all()
    for analysis_id, owner_id in analysis_rows:
        bind.execute(
            analyses.update()
            .where(analyses.c.id == analysis_id)
            .values(created_by_user_id=owner_id)
        )

    op.alter_column("transcriptions", "uploaded_by_user_id", existing_type=sa.BigInteger(), nullable=False)
    op.alter_column("transcriptions", "original_filename", existing_type=sa.String(length=255), nullable=False)
    op.alter_column("transcriptions", "source_path", existing_type=sa.String(length=1024), nullable=False)
    op.alter_column("transcriptions", "status", existing_type=sa.String(length=32), server_default="uploaded")


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column("transcriptions", "status", existing_type=sa.String(length=32), server_default=None)
    op.drop_index("ix_analyses_created_by_user_id", table_name="analyses")
    op.drop_constraint("fk_analyses_created_by_user_id_users", "analyses", type_="foreignkey")
    op.drop_column("analyses", "created_by_user_id")

    op.drop_index("ix_transcriptions_uploaded_by_user_id", table_name="transcriptions")
    op.drop_constraint("fk_transcriptions_uploaded_by_user_id_users", "transcriptions", type_="foreignkey")
    op.drop_column("transcriptions", "source_path")
    op.drop_column("transcriptions", "original_filename")
    op.drop_column("transcriptions", "uploaded_by_user_id")
