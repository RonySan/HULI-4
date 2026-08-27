"""Continuidade factual da conversa curta da sessão atual."""

from __future__ import annotations

from huli.brain.context import ContextEngine, ContextTurn
from huli.core.contracts import KernelRequest, KernelResponse


class ConversationSkill:
    name = "conversation"
    intents = ("conversation.recap",)

    _DOMAIN_PREFIXES = (
        "project.",
        "task.",
        "agenda.",
        "memory.",
        "knowledge.",
        "daily.",
    )

    def __init__(self, context: ContextEngine) -> None:
        self.context = context

    def can_handle(self, request: KernelRequest) -> bool:
        return str(request.metadata.get("intent") or "") in self.intents

    def handle(self, request: KernelRequest) -> KernelResponse:
        if str(request.metadata.get("role") or "owner") != "owner":
            return self._response(
                request,
                "O resumo da conversa exige acesso do proprietário.",
                ok=False,
            )

        session_id = str(request.metadata.get("session_id") or "default")
        turns = self.context.recent_turns(session_id, limit=10)
        meaningful = tuple(
            turn
            for turn in turns
            if turn.intent.startswith(self._DOMAIN_PREFIXES)
        )
        selected = meaningful[-6:] if meaningful else self._fallback_turns(turns)
        if not selected:
            return self._response(
                request,
                "Ainda não há uma conversa anterior nesta sessão para eu resumir.",
                ok=False,
            )

        snapshot = self.context.snapshot(session_id)
        lines = ["Mais cedo, nesta sessão, tratamos destes pontos:"]
        lines.extend(f"- {self._clean_turn(turn)}" for turn in selected)
        if snapshot.active_project:
            lines.append(f"O projeto ativo continua sendo {snapshot.active_project}.")
        return self._response(request, "\n".join(lines))

    @staticmethod
    def _fallback_turns(turns: tuple[ContextTurn, ...]) -> tuple[ContextTurn, ...]:
        useful = tuple(
            turn
            for turn in turns
            if turn.intent not in {"smalltalk", "conversation.recap", "unknown"}
            and not turn.intent.startswith("journal.")
        )
        return useful[-4:]

    @staticmethod
    def _clean_turn(turn: ContextTurn) -> str:
        value = " ".join(turn.text.split()).strip(" .!?")
        if len(value) > 180:
            value = f"{value[:177].rstrip()}..."
        return f"{value}."

    def _response(
        self,
        request: KernelRequest,
        text: str,
        *,
        ok: bool = True,
    ) -> KernelResponse:
        return KernelResponse(
            request_id=request.request_id,
            text=text,
            handled_by=self.name,
            ok=ok,
        )
