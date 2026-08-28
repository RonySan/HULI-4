"""Controle explícito dos modos de conversação da Huli."""

from __future__ import annotations

import re

from huli.brain.conversation import ConversationEngine, ConversationMode
from huli.brain.normalization import normalize_text
from huli.core.contracts import KernelRequest, KernelResponse


class ConversationModeSkill:
    name = "conversation-mode"
    intents = ("conversation.mode.set", "conversation.mode.query")

    def __init__(self, conversation: ConversationEngine) -> None:
        self._conversation = conversation

    def can_handle(self, request: KernelRequest) -> bool:
        return str(request.metadata.get("intent", "")) in self.intents

    def handle(self, request: KernelRequest) -> KernelResponse:
        intent = str(request.metadata.get("intent", ""))
        session_id = str(request.metadata.get("session_id") or "default")

        if intent == "conversation.mode.query":
            snapshot = self._conversation.snapshot(session_id)
            origin = "manual" if snapshot.override is not None else "automático"
            return KernelResponse(
                request_id=request.request_id,
                text=f"Modo atual: {self._display_name(snapshot.mode)} ({origin}).",
                handled_by=self.name,
            )

        requested = self._extract_mode(request.text)
        try:
            snapshot = self._conversation.set_mode(session_id, requested)
        except ValueError as exc:
            return KernelResponse(
                request_id=request.request_id,
                text=str(exc),
                handled_by=self.name,
                ok=False,
            )

        if requested is ConversationMode.AUTO:
            text = "Modo automático ativado. Vou adaptar o tom ao contexto."
        elif requested is ConversationMode.CASUAL:
            text = "Modo casual ativado. Posso conversar de forma mais leve."
        elif requested is ConversationMode.PROFESSIONAL:
            text = "Modo profissional ativado. Vou manter respostas diretas e objetivas."
        elif requested is ConversationMode.SERIOUS:
            text = "Modo sério ativado. Vou manter respostas objetivas e sem humor."
        else:
            text = "Modo de risco ativado. Segurança e confirmação terão prioridade."

        return KernelResponse(
            request_id=request.request_id,
            text=text,
            handled_by=self.name,
        )

    @staticmethod
    def _extract_mode(text: str) -> ConversationMode:
        normalized = normalize_text(text)
        match = re.search(
            r"\b(?:automatico|auto|casual|profissional|serio|risco|seguro)\b",
            normalized,
        )
        if not match:
            raise ValueError("Informe o modo: automático, casual, profissional, sério ou risco.")
        return ConversationEngine.parse_mode(match.group(0))

    @staticmethod
    def _display_name(mode: ConversationMode) -> str:
        labels = {
            ConversationMode.AUTO: "automático",
            ConversationMode.CASUAL: "casual",
            ConversationMode.PROFESSIONAL: "profissional",
            ConversationMode.SERIOUS: "sério",
            ConversationMode.RISK: "risco",
        }
        return labels[mode]


__all__ = ["ConversationModeSkill"]
