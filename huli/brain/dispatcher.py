"""Roteamento consciente de intenção para o cérebro básico da Huli."""

from __future__ import annotations

from huli.brain.intent import IntentEngine, IntentName
from huli.core.contracts import KernelHandler, KernelRequest, KernelResponse
from huli.core.events import EventBus
from huli.skills.registry import SkillRegistry


_PENDING_MESSAGES = {
    IntentName.TIME_QUERY: "Entendi que você quer saber o horário, mas essa capacidade ainda não está ativa.",
    IntentName.AGENDA_QUERY: "Entendi que você quer consultar a agenda, mas o módulo Agenda ainda não está ativo.",
    IntentName.TASK_CREATE: "Entendi que você quer criar uma tarefa, mas o Planner ainda não está ativo.",
    IntentName.SMALL_TALK: "Entendi que você está conversando comigo, mas o módulo Small Talk ainda não está ativo.",
    IntentName.PROJECT_QUERY: "Entendi que você quer consultar um projeto, mas o Project Context ainda não está ativo.",
}


class BrainDispatcher(KernelHandler):
    """Classifica a intenção e delega a execução para as Skills existentes."""

    def __init__(
        self,
        intents: IntentEngine,
        skills: SkillRegistry,
        event_bus: EventBus,
    ) -> None:
        self._intents = intents
        self._skills = skills
        self._event_bus = event_bus

    def handle(self, request: KernelRequest) -> KernelResponse:
        match = self._intents.classify(request.text)
        self._event_bus.publish(
            "brain.intent.classified",
            {
                "request_id": request.request_id,
                "intent": match.intent.value,
                "confidence": match.confidence,
                "normalized_text": match.normalized_text,
                "matched_rule": match.metadata.get("matched_rule", "none"),
            },
        )

        skill = self._skills.resolve(request)
        if skill is not None:
            return skill.handle(request)

        pending_message = _PENDING_MESSAGES.get(match.intent)
        if pending_message is not None:
            return KernelResponse(
                request_id=request.request_id,
                text=pending_message,
                handled_by="brain-dispatcher",
                ok=False,
            )

        return KernelResponse(
            request_id=request.request_id,
            text="Ainda não reconheço uma capacidade segura para essa solicitação.",
            handled_by="brain-dispatcher",
            ok=False,
        )
