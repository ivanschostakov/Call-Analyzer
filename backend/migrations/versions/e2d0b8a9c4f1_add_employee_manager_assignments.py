"""add employee manager assignments

Revision ID: e2d0b8a9c4f1
Revises: c31e5f0e219b
Create Date: 2026-03-30 23:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e2d0b8a9c4f1"
down_revision: Union[str, Sequence[str], None] = "c31e5f0e219b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("employees", sa.Column("manager_user_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        "fk_employees_manager_user_id_users",
        "employees",
        "users",
        ["manager_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(op.f("ix_employees_manager_user_id"), "employees", ["manager_user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_employees_manager_user_id"), table_name="employees")
    op.drop_constraint("fk_employees_manager_user_id_users", "employees", type_="foreignkey")
    op.drop_column("employees", "manager_user_id")
