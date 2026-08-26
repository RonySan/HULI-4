"""Kernel mínimo da Huli.

O Kernel coordena a entrada e a saída. Ele não contém regras de negócio e não
conhece implementações concretas de Skills, memória, IA ou infraestrutura.
"""

from __future__ import annotations

from typing import Mapping

from huli.core.contracts import KernelHandler, KernelRequest, KernelResponse
from huli.core.events import EventBus


class Kernel:
    """Núcleo coordenador da Huli."""

    def __init__(self, handler: KernelHandler | None = None, event_bus: EventBus | None = None) -> None:
        self._handler = handler
        self._event_bus = event_bus

    def process(self, text: str, metadata: Mapping[str, object] | None = None) -> KernelResponse:
        request = KernelRequest.from_text(text, metadata=metadata)
        self._publish("kernel.request.received", {"request_id": request.request_id, "text": request.text, "metadata": dict(request.metadata)})
        if self._handler is not None:
            response = self._handler.handle(request)
            if response.request_id != request.request_id:
                raise RuntimeError("O handler retornou uma resposta com request_id inválido.")
        else:
            response = KernelResponse(request_id=request.request_id, text="Kernel ativo. Mensagem recebida com sucesso; o sistema de Skills ainda não foi conectado.", handled_by="kernel")
        self._publish("kernel.response.created", {"request_id": response.request_id, "text": response.text, "handled_by": response.handled_by, "ok": response.ok})
        return response

    def _publish(self, event_name: str, payload: dict[str, object]) -> None:
        if self._event_bus is not None:
            self._event_bus.publish(event_name, payload)
