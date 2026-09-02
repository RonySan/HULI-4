"""Skill mínima usada para validar a fundação da Huli."""

from __future__ import annotations

from huli.brain.normalization import normalize_text
from huli.core.contracts import KernelRequest, KernelResponse


class FoundationSkill:
    """Capacidade técnica temporária da Fase 0."""

    name = "foundation"

    _HELP = frozenset(
        {
            "ajuda",
            "o que voce sabe fazer",
            "o que voce sabe fazer ate agora",
            "quais sao suas capacidades",
            "quais suas capacidades",
            "comandos",
        }
    )

    def can_handle(self, request: KernelRequest) -> bool:
        text = normalize_text(request.text)
        return text in {
            "ping",
            "status",
            "status huli",
            "teste",
            "teste skill",
        } | self._HELP

    def handle(self, request: KernelRequest) -> KernelResponse:
        if normalize_text(request.text) in self._HELP:
            text = (
                "Posso conversar, informar hora e data, consultar agenda e tarefas, "
                "acompanhar projetos, memória e conhecimento, além do diário privado. "
                "Também posso abrir programas instalados e ouvir pelo botão ou pela "
                "ativação ‘Huli’."
            )
        else:
            text = "Huli ativa. Kernel e Skill Registry operacionais."
        return KernelResponse(
            request_id=request.request_id,
            text=text,
            handled_by=self.name,
        )
