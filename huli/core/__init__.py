"""Núcleo de coordenação da Huli.

O pacote `core` expõe apenas contratos centrais, eventos internos e o Kernel.
Regras de domínio ficam fora daqui por definição arquitetural.
"""

from huli.core.contracts import InvalidKernelInput, KernelRequest, KernelResponse
from huli.core.events import Event, EventBus
from huli.core.kernel import Kernel

__all__ = [
    "Event",
    "EventBus",
    "InvalidKernelInput",
    "Kernel",
    "KernelRequest",
    "KernelResponse",
]
