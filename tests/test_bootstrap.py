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
    assert runtime.events.subscriber_count("kernel.request.received") == 1
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

    pending = runtime.kernel.process("que horas são?")
    assert pending.handled_by == "brain-dispatcher"
    assert "horário" in pending.text

    latest = runtime.interactions.latest(2)
    assert len(latest) == 2
    assert latest[0].user_text == "que horas são?"
    assert latest[1].user_text == "status huli"
