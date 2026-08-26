"""Roteamento consciente de intenção para o cérebro básico da Huli."""

from __future__ import annotations

from dataclasses import replace

from huli.brain.context import ContextEngine
from huli.brain.intent import IntentEngine, IntentName
from huli.core.contracts import KernelHandler, KernelRequest, KernelResponse
from huli.core.events import EventBus
from huli.skills.registry import SkillRegistry


class BrainDispatcher(KernelHandler):
    def __init__(self, intents: IntentEngine, context: ContextEngine, skills: SkillRegistry, event_bus: EventBus) -> None:
        self._intents = intents
        self._context = context
        self._skills = skills
        self._event_bus = event_bus

    def handle(self, request: KernelRequest) -> KernelResponse:
        match = self._intents.classify(request.text)
        session_id = str(request.metadata.get("session_id") or "default")
        snapshot = self._context.snapshot(session_id)
        metadata = dict(request.metadata)
        metadata.update({"session_id": session_id, "intent": match.intent.value, "intent_confidence": match.confidence, "intent_metadata": dict(match.metadata), "active_project": snapshot.active_project, "last_intent": snapshot.last_intent, "last_topic": snapshot.last_topic})
        enriched = replace(request, metadata=metadata)
        self._event_bus.publish("brain.intent.classified", {"request_id": request.request_id, "session_id": session_id, "intent": match.intent.value, "confidence": match.confidence, "normalized_text": match.normalized_text, "matched_rule": match.metadata.get("matched_rule", "none")})
        skill = self._skills.resolve_intent(match.intent.value) or self._skills.resolve(enriched)
        if skill is not None:
            response = skill.handle(enriched)
        elif match.intent is not IntentName.UNKNOWN:
            response = KernelResponse(request_id=request.request_id, text=f"Entendi a intenção '{match.intent.value}', mas ainda não há uma capacidade ativa para executá-la.", handled_by="brain-dispatcher", ok=False)
        else:
            response = KernelResponse(request_id=request.request_id, text="Ainda não reconheço uma capacidade segura para essa solicitação.", handled_by="brain-dispatcher", ok=False)
        topic = str(enriched.metadata.get("active_project") or "").strip() or None
        current = self._context.observe(session_id, request.text, match.intent.value, topic=topic)
        self._event_bus.publish("brain.context.updated", {"request_id": request.request_id, "session_id": session_id, "last_intent": current.last_intent, "active_project": current.active_project, "turn_count": current.turn_count})
        return response
