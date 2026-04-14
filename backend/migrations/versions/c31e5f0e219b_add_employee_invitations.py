"""add employee invitations

Revision ID: c31e5f0e219b
Revises: b1d7d0c6f3a2
Create Date: 2026-03-30 21:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c31e5f0e219b"
down_revision: Union[str, Sequence[str], None] = "b1d7d0c6f3a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "employee_invitations",
        sa.Column("company_id", sa.BigInteger(), nullable=False),
        sa.Column("invited_by_user_id", sa.BigInteger(), nullable=True),
        sa.Column("accepted_by_user_id", sa.BigInteger(), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.ForeignKeyConstraint(["accepted_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invited_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )
    op.create_index(op.f("ix_employee_invitations_accepted_by_user_id"), "employee_invitations", ["accepted_by_user_id"], unique=False)
    op.create_index(op.f("ix_employee_invitations_company_id"), "employee_invitations", ["company_id"], unique=False)
    op.create_index(op.f("ix_employee_invitations_email"), "employee_invitations", ["email"], unique=False)
    op.create_index(op.f("ix_employee_invitations_expires_at"), "employee_invitations", ["expires_at"], unique=False)
    op.create_index(op.f("ix_employee_invitations_id"), "employee_invitations", ["id"], unique=False)
    op.create_index(op.f("ix_employee_invitations_invited_by_user_id"), "employee_invitations", ["invited_by_user_id"], unique=False)
    op.create_index(op.f("ix_employee_invitations_token"), "employee_invitations", ["token"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_employee_invitations_token"), table_name="employee_invitations")
    op.drop_index(op.f("ix_employee_invitations_invited_by_user_id"), table_name="employee_invitations")
    op.drop_index(op.f("ix_employee_invitations_id"), table_name="employee_invitations")
    op.drop_index(op.f("ix_employee_invitations_expires_at"), table_name="employee_invitations")
    op.drop_index(op.f("ix_employee_invitations_email"), table_name="employee_invitations")
    op.drop_index(op.f("ix_employee_invitations_company_id"), table_name="employee_invitations")
    op.drop_index(op.f("ix_employee_invitations_accepted_by_user_id"), table_name="employee_invitations")
    op.drop_table("employee_invitations")
