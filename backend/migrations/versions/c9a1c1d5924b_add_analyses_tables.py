"""add analyses tables

Revision ID: c9a1c1d5924b
Revises: 6606d000f442
Create Date: 2026-03-30 12:39:17.514087

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'c9a1c1d5924b'
down_revision: Union[str, Sequence[str], None] = '6606d000f442'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    criterion_answer_type = postgresql.ENUM(
        "text",
        "percentage",
        "boolean",
        name="criterion_answer_type",
        create_type=False,
    )

    op.create_table(
        "analyses",
        sa.Column("company_id", sa.BigInteger(), nullable=False),
        sa.Column("transcription_id", sa.BigInteger(), nullable=True),
        sa.Column("template_id", sa.BigInteger(), nullable=True),
        sa.Column("template_name", sa.String(length=120), nullable=True),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["template_id"], ["templates.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["transcription_id"], ["transcriptions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_analyses_company_id"), "analyses", ["company_id"], unique=False)
    op.create_index(op.f("ix_analyses_id"), "analyses", ["id"], unique=False)
    op.create_index(op.f("ix_analyses_template_id"), "analyses", ["template_id"], unique=False)
    op.create_index(op.f("ix_analyses_transcription_id"), "analyses", ["transcription_id"], unique=False)

    op.create_table(
        "analysis_results",
        sa.Column("analysis_id", sa.BigInteger(), nullable=False),
        sa.Column("criterion_id", sa.BigInteger(), nullable=True),
        sa.Column("criterion_name", sa.String(length=160), nullable=False),
        sa.Column("criterion_description", sa.Text(), nullable=True),
        sa.Column("criterion_prompt", sa.Text(), nullable=True),
        sa.Column("answer_type", criterion_answer_type, nullable=False),
        sa.Column("answer_text", sa.Text(), nullable=True),
        sa.Column("answer_bool", sa.Boolean(), nullable=True),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("position", sa.Integer(), server_default="0", nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["analysis_id"], ["analyses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["criterion_id"], ["criteria.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("analysis_id", "criterion_id", name="uq_analysis_results_analysis_criterion"),
        sa.UniqueConstraint("analysis_id", "position", name="uq_analysis_results_analysis_position"),
    )
    op.create_index(op.f("ix_analysis_results_analysis_id"), "analysis_results", ["analysis_id"], unique=False)
    op.create_index(op.f("ix_analysis_results_criterion_id"), "analysis_results", ["criterion_id"], unique=False)
    op.create_index(op.f("ix_analysis_results_id"), "analysis_results", ["id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_analysis_results_id"), table_name="analysis_results")
    op.drop_index(op.f("ix_analysis_results_criterion_id"), table_name="analysis_results")
    op.drop_index(op.f("ix_analysis_results_analysis_id"), table_name="analysis_results")
    op.drop_table("analysis_results")

    op.drop_index(op.f("ix_analyses_transcription_id"), table_name="analyses")
    op.drop_index(op.f("ix_analyses_template_id"), table_name="analyses")
    op.drop_index(op.f("ix_analyses_id"), table_name="analyses")
    op.drop_index(op.f("ix_analyses_company_id"), table_name="analyses")
    op.drop_table("analyses")
