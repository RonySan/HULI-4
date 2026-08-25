"""Testes da composição de dependências da Huli."""

from pathlib import Path

from huli.bootstrap import build_runtime
from huli.core import Event
from huli.infrastructure import Settings


def test_build_runtime_connects_foundation_components(tmp_path: Path) -> None:
    runtime = build_runtime(
        Settings(environment="test", log_level="CRITICAL", data_dir=tmp_path)
    )

    assert runtime.settings.environment == "test"
    assert runtime.skills.names == ("foundation",)
    assert runtime.events.subscriber_count("kernel.request.received") == 2
    assert runtime.events.subscriber_count("kernel.response.created") == 1
    assert runtime.database.schema_version() == 2

    classified: list[Event] = []
    runtime.events.subscribe("brain.intent.classified", classified.append)

    response = runtime.kernel.process("status huli")
    assert response.handled_by == "foundation"
    assert response.ok is True
    assert "Kernel e Skill Registry" in response.text

    assert len(classified) == 1
    assert classified[0].payload["intent"] == "system.status"

    latest = runtime.interactions.latest(1)
    assert len(latest) == 1
    assert latest[0].user_text == "status huli"
    assert latest[0].handled_by == "foundation"
