"""add boolean criterion answer type

Revision ID: 6606d000f442
Revises: 428ec0c6c359
Create Date: 2026-03-30 12:27:37.407604

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '6606d000f442'
down_revision: Union[str, Sequence[str], None] = '428ec0c6c359'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE criterion_answer_type ADD VALUE IF NOT EXISTS 'boolean'")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("ALTER TABLE criteria ALTER COLUMN answer_type DROP DEFAULT")
    op.execute("UPDATE criteria SET answer_type = 'text' WHERE answer_type = 'boolean'")
    op.execute("ALTER TYPE criterion_answer_type RENAME TO criterion_answer_type_old")

    criterion_answer_type = postgresql.ENUM(
        "text",
        "percentage",
        name="criterion_answer_type",
        create_type=False,
    )
    criterion_answer_type.create(op.get_bind(), checkfirst=False)

    op.execute(
        """
        ALTER TABLE criteria
        ALTER COLUMN answer_type TYPE criterion_answer_type
        USING answer_type::text::criterion_answer_type
        """
    )
    op.execute("DROP TYPE criterion_answer_type_old")
    op.execute("ALTER TABLE criteria ALTER COLUMN answer_type SET DEFAULT 'text'")
