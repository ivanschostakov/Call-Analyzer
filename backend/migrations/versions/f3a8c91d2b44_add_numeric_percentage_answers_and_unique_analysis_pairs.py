"""add numeric percentage answers and active analysis pairs

Revision ID: f3a8c91d2b44
Revises: 9a7c4f1b2d33
Create Date: 2026-04-03 09:15:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "f3a8c91d2b44"
down_revision: str | Sequence[str] | None = "9a7c4f1b2d33"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _parse_percentage_answer(raw_value: str | None) -> int | None:
    if raw_value is None:
        return None

    normalized = raw_value.strip().replace("%", "").replace(",", ".")
    if not normalized:
        return None

    try:
        parsed_value = round(float(normalized))
    except ValueError:
        return None

    if not 0 <= parsed_value <= 100:
        return None
    return int(parsed_value)


def upgrade() -> None:
    op.add_column("analysis_results", sa.Column("answer_number", sa.Integer(), nullable=True))
    op.add_column("analyses", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("analyses", sa.Column("active_key", sa.Integer(), nullable=True))

    bind = op.get_bind()
    analysis_results = sa.table(
        "analysis_results",
        sa.column("id", sa.BigInteger()),
        sa.column("answer_type", sa.String()),
        sa.column("answer_text", sa.Text()),
        sa.column("answer_number", sa.Integer()),
    )
    analyses = sa.table(
        "analyses",
        sa.column("id", sa.BigInteger()),
        sa.column("transcription_id", sa.BigInteger()),
        sa.column("template_id", sa.BigInteger()),
        sa.column("created_at", sa.DateTime()),
        sa.column("is_active", sa.Boolean()),
        sa.column("active_key", sa.Integer()),
    )

    rows = bind.execute(
        sa.select(
            analysis_results.c.id,
            analysis_results.c.answer_text,
        ).where(sa.cast(analysis_results.c.answer_type, sa.Text()) == "percentage")
    ).all()
    for row in rows:
        parsed_value = _parse_percentage_answer(row.answer_text)
        if parsed_value is None:
            continue
        bind.execute(
            analysis_results.update()
            .where(analysis_results.c.id == row.id)
            .values(answer_number=parsed_value)
        )

    bind.execute(
        analyses.update()
        .values(is_active=True, active_key=1)
    )

    analysis_rows = bind.execute(
        sa.select(
            analyses.c.id,
            analyses.c.transcription_id,
            analyses.c.template_id,
            analyses.c.created_at,
        ).order_by(
            analyses.c.transcription_id.asc(),
            analyses.c.template_id.asc(),
            analyses.c.created_at.desc(),
            analyses.c.id.desc(),
        )
    ).all()
    active_pairs: set[tuple[int, int]] = set()
    for row in analysis_rows:
        if row.transcription_id is None or row.template_id is None:
            continue

        pair = (row.transcription_id, row.template_id)
        is_active = pair not in active_pairs
        if is_active:
            active_pairs.add(pair)
        bind.execute(
            analyses.update()
            .where(analyses.c.id == row.id)
            .values(is_active=is_active, active_key=1 if is_active else None)
        )

    op.create_unique_constraint(
        "uq_analyses_transcription_template_active",
        "analyses",
        ["transcription_id", "template_id", "active_key"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_analyses_transcription_template_active", "analyses", type_="unique")
    op.drop_column("analyses", "active_key")
    op.drop_column("analyses", "is_active")
    op.drop_column("analysis_results", "answer_number")
