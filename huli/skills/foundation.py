"""Skill mínima usada para validar a fundação da Huli."""

from __future__ import annotations

from huli.core.contracts import KernelRequest, KernelResponse


class FoundationSkill:
    """Capacidade técnica temporária da Fase 0."""

    name = "foundation"

    def can_handle(self, request: KernelRequest) -> bool:
        text = request.text.casefold()
        return text in {"ping", "status", "status huli", "teste", "teste skill"}

    def handle(self, request: KernelRequest) -> KernelResponse:
        return KernelResponse(
            request_id=request.request_id,
            text="Huli ativa. Kernel e Skill Registry operacionais.",
            handled_by=self.name,
        )
