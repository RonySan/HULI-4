"""Kernel mínimo da Huli.

O Kernel coordena a entrada e a saída. Ele não contém regras de negócio e não
conhece implementações concretas de Skills, memória, IA ou infraestrutura.
"""

from __future__ import annotations

from huli.core.contracts import KernelHandler, KernelRequest, KernelResponse


class Kernel:
    """Núcleo coordenador da Huli.

    Nesta fase, o Kernel aceita um `KernelHandler` opcional. Enquanto o sistema de
    Skills ainda não existe, ele responde com uma mensagem de estado controlada.
    Quando o próximo módulo for implementado, o Skill Registry poderá cumprir esse
    contrato sem exigir reescrita do Kernel.
    """

    def __init__(self, handler: KernelHandler | None = None) -> None:
        self._handler = handler

    def process(self, text: str) -> KernelResponse:
        """Recebe texto bruto, valida a entrada e devolve uma resposta estruturada."""
        request = KernelRequest.from_text(text)

        if self._handler is not None:
            response = self._handler.handle(request)
            if response.request_id != request.request_id:
                raise RuntimeError("O handler retornou uma resposta com request_id inválido.")
            return response

        return KernelResponse(
            request_id=request.request_id,
            text=(
                "Kernel ativo. Mensagem recebida com sucesso; "
                "o sistema de Skills será conectado na próxima etapa."
            ),
            handled_by="kernel",
        )
