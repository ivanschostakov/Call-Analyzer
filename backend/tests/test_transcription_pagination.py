from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine, insert
from sqlalchemy.dialects import postgresql

from src.database.crud.transcriptions import list_transcription_summaries
from src.database.models import Transcription, TranscriptionFavorite, User
from src.enums import TranscriptionStatus


class LocalSession:
    """Run real list SQL on isolated SQLite without a PostgreSQL service."""

    def __init__(self, connection):
        self.connection = connection
        self.statements = []

    async def scalar(self, statement):
        self.statements.append(statement)
        return self.connection.scalar(statement)

    async def execute(self, statement):
        self.statements.append(statement)
        return self.connection.execute(statement)


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    for model in (User, Transcription, TranscriptionFavorite):
        model.__table__.create(engine)
    with engine.begin() as connection:
        connection.execute(insert(User), [
            dict(id=i, name=f"User {i}", surname="Test", email=f"{i}@test.example", password_hash="unused")
            for i in (1, 2, 3)
        ])
        now = datetime(2026, 10, 20, 12)
        connection.execute(insert(Transcription), [
            dict(
                id=i, company_id=1 if i <= 1419 else 2,
                uploaded_by_user_id=2 if i % 3 else 3,
                detected_employee_user_id=None if i % 3 == 0 else (2 if i % 3 == 1 else 3),
                file_id=f"file-{i}", original_filename=f"call-{i}.wav",
                source_path="unused", file_path="unused",
                status="queued" if i % 5 == 0 else "completed",
                text="Transcript " * 1000, segments=[dict(start=0, end=1, text="segment " * 1000)],
                error_message="error " * 1000,
                created_at=now, updated_at=now + timedelta(days=i),
                call_started_at=now if i % 2 else None,
            )
            for i in range(1, 1421)
        ])
        connection.execute(insert(TranscriptionFavorite), [
            dict(transcription_id=1419, user_id=1),
            dict(transcription_id=1418, user_id=2),
        ])
        yield LocalSession(connection)
    engine.dispose()


@pytest.mark.asyncio
async def test_sql_pagination_is_bounded_deterministic_and_lightweight(db):
    first, total, page = await list_transcription_summaries(db, 1, 1, visible_user_ids=None)
    second, _, _ = await list_transcription_summaries(db, 1, 1, visible_user_ids=None, page=2)
    assert total == 1419
    assert page == 1
    assert len(first) == len(second) == 25
    assert [row["id"] for row in first] == list(range(1419, 1394, -1))
    assert [row["id"] for row in second] == list(range(1394, 1369, -1))
    assert first[0]["is_favorite"] is True
    assert first[1]["is_favorite"] is False
    assert first[0]["uploaded_by_display_name"] == "User 3 Test"
    assert all(len(row["text_preview"]) == 180 and len(row["error_message"]) == 500 for row in first)
    assert all("text" not in row and "segments" not in row and "source_path" not in row for row in first)
    sql = str(db.statements[1].compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
    assert "LIMIT 25 OFFSET 0" in sql
    assert "transcriptions.segments" not in sql
    assert "password_hash" not in sql
    assert "coalesce(transcriptions.call_started_at, transcriptions.created_at) DESC, transcriptions.id DESC" in sql


@pytest.mark.asyncio
async def test_last_page_and_shrinking_result_clamp(db):
    rows, total, page = await list_transcription_summaries(db, 1, 1, visible_user_ids=None, page=999)
    assert (total, page, len(rows)) == (1419, 57, 19)
    rows, total, page = await list_transcription_summaries(
        db, 1, 1, visible_user_ids=None, page=57, favorites_only=True,
    )
    assert (total, page, len(rows)) == (1, 1, 1)


@pytest.mark.asyncio
@pytest.mark.parametrize("employee", ["all", "2", "3", "unresolved"])
async def test_filters_and_count_use_same_visible_scope(db, employee):
    rows, total, _ = await list_transcription_summaries(
        db, 1, 1, visible_user_ids=[2], employee=employee,
        status=TranscriptionStatus.COMPLETED, page_size=100,
    )
    expected = [
        i for i in range(1, 1420)
        if i % 3 == 1 and i % 5 != 0 and employee in ("all", "2")
    ]
    assert total == len(expected)
    assert [row["id"] for row in rows] == sorted(expected, reverse=True)[:100]


@pytest.mark.asyncio
async def test_visibility_falls_back_to_uploader_only_when_unassigned(db):
    rows, total, _ = await list_transcription_summaries(
        db, 1, 1, visible_user_ids=[3], employee="unresolved", page_size=100,
    )
    assert total == 473
    assert all(row["detected_employee_user_id"] is None and row["uploaded_by_user_id"] == 3 for row in rows)
    rows, total, _ = await list_transcription_summaries(
        db, 1, 1, visible_user_ids=[2], employee="3",
    )
    assert rows == []
    assert total == 0  # Uploader 2 cannot see calls assigned to employee 3.


@pytest.mark.asyncio
@pytest.mark.parametrize("visible_user_ids", [[], [2]])
async def test_favorites_cannot_bypass_visibility(db, visible_user_ids):
    rows, total, page = await list_transcription_summaries(
        db, 1, 1, visible_user_ids=visible_user_ids, favorites_only=True,
    )
    assert (rows, total, page) == ([], 0, 1)


@pytest.mark.asyncio
async def test_favorites_are_personal_and_company_scoped(db):
    rows, total, _ = await list_transcription_summaries(
        db, 1, 2, visible_user_ids=None, favorites_only=True,
    )
    assert total == 1
    assert rows[0]["id"] == 1418
    rows, total, _ = await list_transcription_summaries(db, 2, 1, visible_user_ids=None)
    assert total == 1
    assert rows[0]["id"] == 1420
    assert not rows[0]["is_favorite"]


@pytest.mark.asyncio
async def test_null_text_preview_and_call_date_order(db):
    from sqlalchemy import update

    db.connection.execute(update(Transcription).where(Transcription.id == 1).values(
        call_started_at=datetime(2026, 10, 21), text=None, segments=[],
    ))
    rows, _, _ = await list_transcription_summaries(db, 1, 1, visible_user_ids=None)
    assert rows[0]["id"] == 1
    assert rows[0]["text_preview"] is None
    assert not rows[0]["has_text"]
