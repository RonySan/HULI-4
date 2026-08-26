"""Entrada controlada para aprendizado automático de memórias candidatas."""

from __future__ import annotations

from huli.core.events import Event, EventBus
from huli.memory.engine import MemoryEngine
from huli.memory.models import MemoryCandidate, MemoryKind
from huli.memory.policy import MemoryPolicyError


class MemoryCandidateObserver:
    """Aceita apenas candidatos explícitos do sistema e aplica a política central."""

    def __init__(self, event_bus: EventBus, engine: MemoryEngine) -> None:
        self._events = event_bus
        self._engine = engine
        event_bus.subscribe("memory.candidate", self._on_candidate)

    def _on_candidate(self, event: Event) -> None:
        payload = event.payload
        try:
            kind = MemoryKind(str(payload.get("kind", MemoryKind.SEMANTIC.value)))
            confidence = float(payload.get("confidence", 0.0))
            metadata = payload.get("metadata", {})
            candidate = MemoryCandidate(
                owner=str(payload.get("owner", "")).strip(),
                content=str(payload.get("content", "")).strip(),
                kind=kind,
                subject=str(payload.get("subject", "")).strip() or None,
                project=str(payload.get("project", "")).strip() or None,
                confidence=confidence,
                metadata=dict(metadata) if isinstance(metadata, dict) else {},
            )
            memory = self._engine.remember_candidate(candidate)
        except (MemoryPolicyError, ValueError) as exc:
            self._events.publish(
                "memory.candidate.rejected",
                {
                    "candidate_event_id": event.event_id,
                    "reason": str(exc),
                },
            )
            return

        self._events.publish(
            "memory.candidate.accepted",
            {
                "candidate_event_id": event.event_id,
                "memory_id": memory.id,
                "owner": memory.owner,
            },
        )
