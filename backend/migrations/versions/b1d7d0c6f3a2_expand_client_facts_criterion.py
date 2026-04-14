"""expand client facts criterion

Revision ID: b1d7d0c6f3a2
Revises: 7ef64585d4f4, 240bb2ac22ef
Create Date: 2026-03-30 21:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b1d7d0c6f3a2"
down_revision: Union[str, Sequence[str], None] = ("7ef64585d4f4", "240bb2ac22ef")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_TEMPLATE_NAME = "Базовый шаблон"
CRITERION_NAME = "Факты о клиенте"
OLD_DESCRIPTION = "Какие факты о клиенте были выявлены?"
NEW_DESCRIPTION = "Какие явные факты о клиенте удалось узнать из разговора?"
OLD_PROMPT = (
    "Выдели конкретные факты, которые менеджер узнал о клиенте: компания, ситуация, процессы, контекст, "
    "ограничения, сроки, бюджет, роль и другие объективные сведения."
)
NEW_PROMPT = (
    "Собери любые явно названные или надежно подтвержденные разговором факты о клиенте. Включай не только "
    "деловой контекст, но и персональные сведения, если они прозвучали: имя, фамилия, должность, компания, "
    "город, семья, дети, питомцы, интересы, предпочтения, привычки, опыт, особенности ситуации, ограничения, "
    "сроки, бюджет, роль и другие конкретные факты. Не выдумывай и не расширяй список сверх того, что реально "
    "следует из разговора."
)


def upgrade() -> None:
    connection = op.get_bind()

    connection.execute(
        sa.text(
            """
            UPDATE criteria AS c
            SET description = :new_description
            FROM templates AS t
            WHERE c.template_id = t.id
              AND t.name = :template_name
              AND c.name = :criterion_name
              AND (c.description = :old_description OR c.description IS NULL)
            """
        ),
        {
            "template_name": DEFAULT_TEMPLATE_NAME,
            "criterion_name": CRITERION_NAME,
            "old_description": OLD_DESCRIPTION,
            "new_description": NEW_DESCRIPTION,
        },
    )

    connection.execute(
        sa.text(
            """
            UPDATE criteria AS c
            SET prompt = :new_prompt
            FROM templates AS t
            WHERE c.template_id = t.id
              AND t.name = :template_name
              AND c.name = :criterion_name
              AND (c.prompt = :old_prompt OR c.prompt IS NULL)
            """
        ),
        {
            "template_name": DEFAULT_TEMPLATE_NAME,
            "criterion_name": CRITERION_NAME,
            "old_prompt": OLD_PROMPT,
            "new_prompt": NEW_PROMPT,
        },
    )


def downgrade() -> None:
    connection = op.get_bind()

    connection.execute(
        sa.text(
            """
            UPDATE criteria AS c
            SET description = :old_description
            FROM templates AS t
            WHERE c.template_id = t.id
              AND t.name = :template_name
              AND c.name = :criterion_name
              AND c.description = :new_description
            """
        ),
        {
            "template_name": DEFAULT_TEMPLATE_NAME,
            "criterion_name": CRITERION_NAME,
            "old_description": OLD_DESCRIPTION,
            "new_description": NEW_DESCRIPTION,
        },
    )

    connection.execute(
        sa.text(
            """
            UPDATE criteria AS c
            SET prompt = :old_prompt
            FROM templates AS t
            WHERE c.template_id = t.id
              AND t.name = :template_name
              AND c.name = :criterion_name
              AND c.prompt = :new_prompt
            """
        ),
        {
            "template_name": DEFAULT_TEMPLATE_NAME,
            "criterion_name": CRITERION_NAME,
            "old_prompt": OLD_PROMPT,
            "new_prompt": NEW_PROMPT,
        },
    )
