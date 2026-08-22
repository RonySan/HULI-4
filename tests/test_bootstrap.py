"""Testes da composição de dependências da Huli."""

from huli.bootstrap import build_runtime
from huli.infrastructure import Settings


def test_build_runtime_connects_foundation_components() -> None:
    runtime = build_runtime(Settings(environment="test", log_level="CRITICAL"))

    assert runtime.settings.environment == "test"
    assert runtime.skills.names == ("foundation",)
    assert runtime.events.subscriber_count("kernel.request.received") == 0

    response = runtime.kernel.process("ping")
    assert response.handled_by == "foundation"
    assert response.ok is True
    assert "Kernel e Skill Registry" in response.text
