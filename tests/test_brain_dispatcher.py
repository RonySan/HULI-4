"""Testes do BrainDispatcher da Fase 1."""

from huli.brain import BrainDispatcher, ContextEngine, IntentEngine
from huli.core import Event, EventBus, KernelRequest
from huli.skills import FoundationSkill, SkillRegistry


def build_dispatcher() -> tuple[BrainDispatcher, EventBus]:
    events = EventBus()
    skills = SkillRegistry()
    skills.register(FoundationSkill())
    dispatcher = BrainDispatcher(
        IntentEngine(),
        ContextEngine(),
        skills,
        events,
    )
    return dispatcher, events


def test_foundation_skill_still_handles_ping() -> None:
    dispatcher, _events = build_dispatcher()
    request = KernelRequest.from_text("ping")

    response = dispatcher.handle(request)

    assert response.handled_by == "foundation"
    assert response.ok is True


def test_known_intent_without_skill_returns_controlled_message() -> None:
    dispatcher, _events = build_dispatcher()
    request = KernelRequest.from_text("que horas são?")

    response = dispatcher.handle(request)

    assert response.handled_by == "brain-dispatcher"
    assert response.ok is False
    assert "time.query" in response.text
    assert "capacidade ativa" in response.text


def test_unknown_request_keeps_controlled_fallback() -> None:
    dispatcher, _events = build_dispatcher()
    request = KernelRequest.from_text("abrir o chrome")

    response = dispatcher.handle(request)

    assert response.handled_by == "brain-dispatcher"
    assert response.ok is False
    assert "não reconheço" in response.text


def test_dispatcher_publishes_intent_event_once() -> None:
    dispatcher, events = build_dispatcher()
    captured: list[Event] = []
    events.subscribe("brain.intent.classified", captured.append)

    dispatcher.handle(KernelRequest.from_text("oi huli, bom dia"))

    assert len(captured) == 1
    assert captured[0].payload["intent"] == "smalltalk"
