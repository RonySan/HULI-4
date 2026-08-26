"""Integração do Intent Engine com o barramento interno de eventos."""

from __future__ import annotations

from huli.brain.intent import IntentEngine
from huli.core.events import Event, EventBus


class IntentObserver:
    """Classifica requisições do Kernel e publica a intenção sem executar ações."""

    def __init__(self, event_bus: EventBus, engine: IntentEngine) -> None:
        self._event_bus = event_bus
        self._engine = engine
        event_bus.subscribe("kernel.request.received", self._on_request)

    def _on_request(self, event: Event) -> None:
        request_id = str(event.payload.get("request_id", ""))
        text = str(event.payload.get("text", ""))
        match = self._engine.classify(text)

        self._event_bus.publish(
            "brain.intent.classified",
            {
                "request_id": request_id,
                "intent": match.intent.value,
                "confidence": match.confidence,
                "normalized_text": match.normalized_text,
                "matched_rule": match.metadata.get("matched_rule", "none"),
            },
        )
