"""Testes da persistência SQLite da Huli."""

from pathlib import Path

from huli.core import EventBus
from huli.infrastructure import (
    EventRepository,
    InteractionRepository,
    RuntimeRecorder,
    SQLiteDatabase,
)


def test_database_initializes_schema(tmp_path: Path) -> None:
    database = SQLiteDatabase(tmp_path / "huli.db")
    database.initialize()

    assert database.path.exists()
    assert database.schema_version() == 8


def test_runtime_recorder_persists_interaction(tmp_path: Path) -> None:
    database = SQLiteDatabase(tmp_path / "huli.db")
    database.initialize()

    events = EventBus()
    event_repository = EventRepository(database)
    interactions = InteractionRepository(database)
    RuntimeRecorder(events, event_repository, interactions)

    events.publish(
        "kernel.request.received",
        {"request_id": "abc", "text": "ping"},
    )
    events.publish(
        "kernel.response.created",
        {
            "request_id": "abc",
            "text": "pong",
            "handled_by": "foundation",
            "ok": True,
        },
    )

    assert event_repository.count() == 2
    latest = interactions.latest(1)
    assert latest[0].user_text == "ping"
    assert latest[0].response_text == "pong"
