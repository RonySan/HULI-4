"""Testes da composição de dependências da Huli."""

from pathlib import Path

from huli.bootstrap import build_runtime
from huli.core import Event
from huli.infrastructure import Settings


def test_build_runtime_connects_phase3_staging_components(tmp_path: Path) -> None:
    runtime = build_runtime(
        Settings(environment="test", log_level="CRITICAL", data_dir=tmp_path)
    )
    assert runtime.skills.names == (
        "foundation",
        "time",
        "planner",
        "agenda",
        "applications",
        "daily-summary",
        "morning-briefing",
        "smalltalk",
        "conversation",
        "journal",
        "project-context",
        "memory",
        "knowledge",
    )
    assert runtime.database.schema_version() == 8
    assert runtime.journal_vault.is_unlocked("rony") is False
    assert runtime.journal_repository.count_active("rony") == 0
    assert runtime.memory_repository.count_active("rony") == 0
    assert runtime.knowledge_repository.list_entities("rony") == ()

    classified: list[Event] = []
    runtime.events.subscribe("brain.intent.classified", classified.append)

    response = runtime.kernel.process(
        "status huli",
        metadata={"session_id": "bootstrap-test"},
    )
    assert response.handled_by == "foundation"

    time_response = runtime.kernel.process(
        "que horas são?",
        metadata={"session_id": "bootstrap-test"},
    )
    assert time_response.handled_by == "time"

    owner_meta = {
        "session_id": "bootstrap-test",
        "username": "rony",
        "role": "owner",
    }
    memory_response = runtime.kernel.process(
        "lembre que Medynx depende de MySQL",
        metadata=owner_meta,
    )
    assert memory_response.handled_by == "memory"
    assert runtime.memory_repository.count_active("rony") == 1

    knowledge_response = runtime.kernel.process(
        "do que Medynx depende?",
        metadata=owner_meta,
    )
    assert knowledge_response.handled_by == "knowledge"
    assert "MySQL" in knowledge_response.text

    assert len(classified) == 4
    assert classified[0].payload["intent"] == "system.status"
    assert classified[1].payload["intent"] == "time.query"
    assert classified[2].payload["intent"] == "memory.remember"
    assert classified[3].payload["intent"] == "knowledge.relation"
