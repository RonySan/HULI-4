"""Roteamento consciente de intenção para o cérebro da Huli."""

from __future__ import annotations

from dataclasses import replace

from huli.brain.context import ContextEngine
from huli.brain.conversation import ConversationEngine
from huli.brain.intent import IntentEngine, IntentName
from huli.core.contracts import KernelHandler, KernelRequest, KernelResponse
from huli.core.events import EventBus
from huli.skills.registry import SkillRegistry


class BrainDispatcher(KernelHandler):
    def __init__(
        self,
        intents: IntentEngine,
        context: ContextEngine,
        skills: SkillRegistry,
        event_bus: EventBus,
        conversation: ConversationEngine | None = None,
    ) -> None:
        self._intents = intents
        self._context = context
        self._skills = skills
        self._event_bus = event_bus
        self._conversation = conversation or ConversationEngine()

    def handle(self, request: KernelRequest) -> KernelResponse:
        match = self._intents.classify(request.text)
        session_id = str(request.metadata.get("session_id") or "default")
        context_snapshot = self._context.snapshot(session_id)
        conversation_snapshot = self._conversation.analyze(
            session_id,
            request.text,
            match.intent.value,
        )

        metadata = dict(request.metadata)
        metadata.update(
            {
                "session_id": session_id,
                "intent": match.intent.value,
                "intent_confidence": match.confidence,
                "intent_metadata": dict(match.metadata),
                "active_project": context_snapshot.active_project,
                "last_intent": context_snapshot.last_intent,
                "last_topic": context_snapshot.last_topic,
                "conversation_mode": conversation_snapshot.mode.value,
                "conversation_signal": conversation_snapshot.signal.value,
                "humor_allowed": conversation_snapshot.humor_allowed,
                "conversation_turn": conversation_snapshot.turn_count,
            }
        )
        enriched = replace(request, metadata=metadata)

        self._event_bus.publish(
            "brain.intent.classified",
            {
                "request_id": request.request_id,
                "session_id": session_id,
                "intent": match.intent.value,
                "confidence": match.confidence,
                "normalized_text": match.normalized_text,
                "matched_rule": match.metadata.get("matched_rule", "none"),
            },
        )

        skill = self._skills.resolve_intent(match.intent.value) or self._skills.resolve(enriched)
        if skill is not None:
            response = skill.handle(enriched)
        elif match.intent is not IntentName.UNKNOWN:
            response = KernelResponse(
                request_id=request.request_id,
                text=(
                    f"Entendi a intenção '{match.intent.value}', mas ainda não há uma "
                    "capacidade ativa para executá-la."
                ),
                handled_by="brain-dispatcher",
                ok=False,
            )
        else:
            response = KernelResponse(
                request_id=request.request_id,
                text=self._conversation.fallback_text(conversation_snapshot),
                handled_by="brain-dispatcher",
                ok=False,
            )

        topic = str(enriched.metadata.get("active_project") or "").strip() or None
        current = self._context.observe(
            session_id,
            request.text,
            match.intent.value,
            topic=topic,
        )
        self._event_bus.publish(
            "brain.context.updated",
            {
                "request_id": request.request_id,
                "session_id": session_id,
                "last_intent": current.last_intent,
                "active_project": current.active_project,
                "turn_count": current.turn_count,
            },
        )

        final_conversation = self._conversation.snapshot(session_id)
        self._event_bus.publish(
            "brain.conversation.updated",
            {
                "request_id": request.request_id,
                "session_id": session_id,
                "mode": final_conversation.mode.value,
                "override": (
                    final_conversation.override.value
                    if final_conversation.override is not None
                    else None
                ),
                "signal": final_conversation.signal.value,
                "humor_allowed": final_conversation.humor_allowed,
                "turn_count": final_conversation.turn_count,
            },
        )
        return response
