"""Barramento de eventos internos da Huli."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class Event:
    """Evento imutável emitido internamente pela Huli."""

    name: str
    payload: dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: uuid4().hex)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


EventSubscriber = Callable[[Event], None]


class EventBus:
    """Publica eventos síncronos para assinantes registrados."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[EventSubscriber]] = defaultdict(list)

    def subscribe(self, event_name: str, subscriber: EventSubscriber) -> None:
        """Registra um assinante para um evento específico."""
        name = event_name.strip()
        if not name:
            raise ValueError("O nome do evento não pode estar vazio.")
        if subscriber not in self._subscribers[name]:
            self._subscribers[name].append(subscriber)

    def unsubscribe(self, event_name: str, subscriber: EventSubscriber) -> None:
        """Remove um assinante sem falhar quando ele já não existe."""
        subscribers = self._subscribers.get(event_name, [])
        if subscriber in subscribers:
            subscribers.remove(subscriber)
        if not subscribers and event_name in self._subscribers:
            del self._subscribers[event_name]

    def publish(self, event_name: str, payload: dict[str, Any] | None = None) -> Event:
        """Cria e entrega um evento a todos os assinantes atuais."""
        name = event_name.strip()
        if not name:
            raise ValueError("O nome do evento não pode estar vazio.")

        event = Event(name=name, payload=dict(payload or {}))
        for subscriber in tuple(self._subscribers.get(name, ())):
            subscriber(event)
        return event

    def subscriber_count(self, event_name: str) -> int:
        """Retorna a quantidade de assinantes de um evento."""
        return len(self._subscribers.get(event_name, ()))
