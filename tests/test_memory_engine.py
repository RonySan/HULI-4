from pathlib import Path

from huli.core import Event, EventBus
from huli.infrastructure import SQLiteDatabase
from huli.memory import MemoryEngine, MemoryKind, MemoryPolicy, MemoryRepository


def build_engine(tmp_path: Path) -> tuple[MemoryEngine, EventBus]:
    database = SQLiteDatabase(tmp_path / "huli.db")
    database.initialize()
    events = EventBus()
    engine = MemoryEngine(MemoryRepository(database), MemoryPolicy(), events)
    return engine, events


def test_memory_round_trip_and_owner_isolation(tmp_path: Path) -> None:
    engine, _events = build_engine(tmp_path)

    saved = engine.remember(
        owner="rony",
        content="prefiro café sem açúcar",
        kind=MemoryKind.PREFERENCE,
    )
    engine.remember(owner="outro", content="prefiro café forte")

    matches = engine.recall(owner="rony", query="café")

    assert matches[0].id == saved.id
    assert all(memory.owner.casefold() == "rony" for memory in matches)


def test_duplicate_explicit_memory_is_updated_not_duplicated(tmp_path: Path) -> None:
    engine, _events = build_engine(tmp_path)

    first = engine.remember(owner="rony", content="o projeto Atlas usa Python")
    second = engine.remember(owner="rony", content="o projeto Atlas usa Python")

    assert second.id == first.id
    assert engine.repository.count_active("rony") == 1


def test_forget_is_logical_and_removes_memory_from_recall(tmp_path: Path) -> None:
    engine, _events = build_engine(tmp_path)

    saved = engine.remember(owner="rony", content="prefiro café sem açúcar")
    forgotten = engine.forget(owner="rony", target=str(saved.id))

    assert forgotten.is_active is False
    assert engine.recall(owner="rony", query="café") == ()
    assert engine.repository.get(saved.id, "rony").is_active is False


def test_memory_events_are_published(tmp_path: Path) -> None:
    engine, events = build_engine(tmp_path)
    created: list[Event] = []
    recalled: list[Event] = []
    forgotten: list[Event] = []
    events.subscribe("memory.created", created.append)
    events.subscribe("memory.recalled", recalled.append)
    events.subscribe("memory.forgotten", forgotten.append)

    memory = engine.remember(owner="rony", content="o servidor de testes usa Linux")
    engine.recall(owner="rony", query="servidor Linux")
    engine.forget(owner="rony", target=str(memory.id))

    assert created[0].payload["memory_id"] == memory.id
    assert recalled[0].payload["count"] == 1
    assert forgotten[0].payload["memory_id"] == memory.id
