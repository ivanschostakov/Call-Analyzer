from types import SimpleNamespace

import pytest
from sqlalchemy.dialects import postgresql

from src.database.crud.companies import build_list_companies_accessible_to_user_id_statement, update_company
from src.database.schemas import CompanyUpdate


class FailingSession:
    def __init__(self) -> None:
        self.added = None
        self.rolled_back = False
        self.refreshed = False

    def add(self, obj) -> None:
        self.added = obj

    async def commit(self) -> None:
        raise RuntimeError("commit failed")

    async def rollback(self) -> None:
        self.rolled_back = True

    async def refresh(self, obj) -> None:
        self.refreshed = True


@pytest.mark.asyncio
async def test_update_company_rolls_back_when_commit_fails() -> None:
    db = FailingSession()
    company = SimpleNamespace(id=1, name="Elixir", description="Before")

    with pytest.raises(RuntimeError, match="commit failed"):
        await update_company(
            db,
            company,
            CompanyUpdate(description="After"),
        )

    assert db.added is company
    assert db.rolled_back is True
    assert db.refreshed is False


def test_list_companies_accessible_statement_avoids_distinct_on_json_columns() -> None:
    statement = build_list_companies_accessible_to_user_id_statement(3)

    compiled = str(statement.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True})).upper()

    assert "DISTINCT" not in compiled
    assert "EXISTS" in compiled
