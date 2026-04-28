"""add mentor threads and messages

Revision ID: d4f8a61c7b2d
Revises: a2f7d3c4b981
Create Date: 2026-04-28 00:00:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "d4f8a61c7b2d"
down_revision: str | Sequence[str] | None = "a2f7d3c4b981"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "mentor_threads",
        sa.Column("owner_user_id", sa.BigInteger(), nullable=False),
        sa.Column("company_id", sa.BigInteger(), nullable=False),
        sa.Column("template_id", sa.BigInteger(), nullable=True),
        sa.Column("openai_conversation_id", sa.String(length=255), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["template_id"], ["templates.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_mentor_threads_company_id"), "mentor_threads", ["company_id"], unique=False)
    op.create_index(op.f("ix_mentor_threads_id"), "mentor_threads", ["id"], unique=False)
    op.create_index(op.f("ix_mentor_threads_openai_conversation_id"), "mentor_threads", ["openai_conversation_id"], unique=False)
    op.create_index(op.f("ix_mentor_threads_owner_user_id"), "mentor_threads", ["owner_user_id"], unique=False)
    op.create_index(op.f("ix_mentor_threads_template_id"), "mentor_threads", ["template_id"], unique=False)

    op.create_table(
        "mentor_messages",
        sa.Column("thread_id", sa.BigInteger(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("analysis_ids", sa.JSON(), nullable=False),
        sa.Column("selected_columns", sa.JSON(), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("summarized_row_count", sa.Integer(), nullable=False),
        sa.Column("omitted_row_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.ForeignKeyConstraint(["thread_id"], ["mentor_threads.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_mentor_messages_id"), "mentor_messages", ["id"], unique=False)
    op.create_index(op.f("ix_mentor_messages_role"), "mentor_messages", ["role"], unique=False)
    op.create_index(op.f("ix_mentor_messages_thread_id"), "mentor_messages", ["thread_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_mentor_messages_thread_id"), table_name="mentor_messages")
    op.drop_index(op.f("ix_mentor_messages_role"), table_name="mentor_messages")
    op.drop_index(op.f("ix_mentor_messages_id"), table_name="mentor_messages")
    op.drop_table("mentor_messages")
    op.drop_index(op.f("ix_mentor_threads_template_id"), table_name="mentor_threads")
    op.drop_index(op.f("ix_mentor_threads_owner_user_id"), table_name="mentor_threads")
    op.drop_index(op.f("ix_mentor_threads_openai_conversation_id"), table_name="mentor_threads")
    op.drop_index(op.f("ix_mentor_threads_id"), table_name="mentor_threads")
    op.drop_index(op.f("ix_mentor_threads_company_id"), table_name="mentor_threads")
    op.drop_table("mentor_threads")
