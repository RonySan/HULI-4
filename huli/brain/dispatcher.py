"""Roteamento consciente de intenção para o cérebro básico da Huli."""

from __future__ import annotations

from dataclasses import replace

from huli.brain.context import ContextEngine
from huli.brain.intent import IntentEngine
from huli.core.contracts import KernelHandler, KernelRequest, KernelResponse
from huli.core.events import EventBus
from huli.personality import PersonalityEngine
from huli.security.privacy import PRIVATE_JOURNAL_REDACTION, is_private_journal_text
from huli.skills.registry import SkillRegistry


class BrainDispatcher(KernelHandler):
    def __init__(
        self,
        intents: IntentEngine,
        context: ContextEngine,
        skills: SkillRegistry,
        event_bus: EventBus,
        personality: PersonalityEngine | None = None,
    ) -> None:
        self._intents = intents
        self._context = context
        self._skills = skills
        self._event_bus = event_bus
        self._personality = personality

    def handle(self, request: KernelRequest) -> KernelResponse:
        match = self._intents.classify(request.text)
        session_id = str(request.metadata.get("session_id") or "default")
        snapshot = self._context.snapshot(session_id)

        intent_value = match.intent.value
        mode = "casual"
        is_followup = False
        if self._personality is not None:
            decision = self._personality.decide(
                text=request.text,
                intent=intent_value,
                last_intent=snapshot.last_intent,
                active_project=snapshot.active_project,
                metadata=dict(request.metadata),
            )
            intent_value = decision.intent
            mode = decision.mode.value
            is_followup = decision.is_followup
            self._personality.publish_decision(
                request_id=request.request_id,
                session_id=session_id,
                decision=decision,
            )

        metadata = dict(request.metadata)
        metadata.update(
            {
                "session_id": session_id,
                "intent": intent_value,
                "intent_confidence": match.confidence,
                "intent_metadata": dict(match.metadata),
                "active_project": snapshot.active_project,
                "last_intent": snapshot.last_intent,
                "last_topic": snapshot.last_topic,
                "conversation_mode": mode,
                "conversation_followup": is_followup,
            }
        )
        enriched = replace(request, metadata=metadata)

        self._event_bus.publish(
            "brain.intent.classified",
            {
                "request_id": request.request_id,
                "session_id": session_id,
                "intent": intent_value,
                "raw_intent": match.intent.value,
                "confidence": match.confidence,
                "normalized_text": match.normalized_text,
                "matched_rule": match.metadata.get("matched_rule", "none"),
            },
        )

        skill = self._skills.resolve_intent(intent_value) or self._skills.resolve(enriched)
        if skill is not None:
            response = skill.handle(enriched)
        elif intent_value != "unknown":
            response = KernelResponse(
                request_id=request.request_id,
                text=(
                    f"Entendi a intenção '{intent_value}', mas ainda não há uma capacidade "
                    "ativa para executá-la."
                ),
                handled_by="brain-dispatcher",
                ok=False,
            )
        else:
            response = KernelResponse(
                request_id=request.request_id,
                text="Ainda não reconheço uma capacidade segura para essa solicitação.",
                handled_by="brain-dispatcher",
                ok=False,
            )

        topic = str(enriched.metadata.get("active_project") or "").strip() or None
        observed_text = (
            PRIVATE_JOURNAL_REDACTION
            if intent_value.startswith("journal.")
            or is_private_journal_text(request.text)
            else request.text
        )
        current = self._context.observe(
            session_id,
            observed_text,
            intent_value,
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
                "conversation_mode": mode,
            },
        )
        return response
