"""Testes do barramento de eventos internos."""

from huli.core import Event, EventBus, Kernel


def test_event_bus_delivers_event_and_payload() -> None:
    bus = EventBus()
    received: list[Event] = []
    bus.subscribe("demo", received.append)

    emitted = bus.publish("demo", {"value": 42})

    assert received == [emitted]
    assert emitted.name == "demo"
    assert emitted.payload == {"value": 42}


def test_event_bus_does_not_duplicate_same_subscriber() -> None:
    bus = EventBus()
    received: list[Event] = []
    bus.subscribe("demo", received.append)
    bus.subscribe("demo", received.append)
    assert bus.subscriber_count("demo") == 1


def test_event_bus_unsubscribe_is_safe() -> None:
    bus = EventBus()
    received: list[Event] = []
    bus.subscribe("demo", received.append)
    bus.unsubscribe("demo", received.append)
    bus.publish("demo")
    assert received == []


def test_kernel_emits_request_and_response_events() -> None:
    bus = EventBus()
    received: list[str] = []
    bus.subscribe("kernel.request.received", lambda event: received.append(event.name))
    bus.subscribe("kernel.response.created", lambda event: received.append(event.name))

    kernel = Kernel(event_bus=bus)
    kernel.process("teste de evento")

    assert received == ["kernel.request.received", "kernel.response.created"]
