"""Testes da integração do Intent Engine com o EventBus."""

from pathlib import Path

from huli.brain import IntentEngine, IntentObserver
from huli.bootstrap import build_runtime
from huli.core import Event, EventBus
from huli.infrastructure import Settings


def test_intent_observer_publishes_classification() -> None:
    events = EventBus()
    engine = IntentEngine()
    IntentObserver(events, engine)
    captured: list[Event] = []
    events.subscribe("brain.intent.classified", captured.append)

    events.publish(
        "kernel.request.received",
        {"request_id": "abc", "text": "que horas são?"},
    )

    assert len(captured) == 1
    assert captured[0].payload["request_id"] == "abc"
    assert captured[0].payload["intent"] == "time.query"
    assert captured[0].payload["confidence"] == 0.99


def test_runtime_classifies_kernel_requests_without_changing_kernel(tmp_path: Path) -> None:
    runtime = build_runtime(
        Settings(environment="test", log_level="CRITICAL", data_dir=tmp_path)
    )
    captured: list[Event] = []
    runtime.events.subscribe("brain.intent.classified", captured.append)

    response = runtime.kernel.process("status huli")

    assert response.handled_by == "foundation"
    assert captured[0].payload["intent"] == "system.status"
