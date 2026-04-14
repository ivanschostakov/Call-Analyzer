"""add company vector store id

Revision ID: 240bb2ac22ef
Revises: 0f8d5fbb4a11
Create Date: 2026-03-30 16:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "240bb2ac22ef"
down_revision: Union[str, Sequence[str], None] = "0f8d5fbb4a11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("companies", sa.Column("vector_store_id", sa.String(length=255), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("companies", "vector_store_id")
