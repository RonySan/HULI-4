"""Testes da composição de dependências da Huli."""

from pathlib import Path

from huli.bootstrap import build_runtime
from huli.core import Event
from huli.infrastructure import Settings


def test_build_runtime_connects_phase2_components(tmp_path: Path) -> None:
    runtime = build_runtime(
        Settings(environment="test", log_level="CRITICAL", data_dir=tmp_path)
    )
    assert runtime.skills.names == (
        "foundation",
        "time",
        "planner",
        "agenda",
        "daily-summary",
        "smalltalk",
        "project-context",
        "memory",
    )
    assert runtime.database.schema_version() == 5
    assert runtime.memory_repository.count_active("rony") == 0

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

    memory_response = runtime.kernel.process(
        "lembre que eu prefiro café sem açúcar",
        metadata={
            "session_id": "bootstrap-test",
            "username": "rony",
            "role": "owner",
        },
    )
    assert memory_response.handled_by == "memory"
    assert runtime.memory_repository.count_active("rony") == 1

    assert len(classified) == 3
    assert classified[0].payload["intent"] == "system.status"
    assert classified[1].payload["intent"] == "time.query"
    assert classified[2].payload["intent"] == "memory.remember"
