"""Núcleo de coordenação da Huli.

O pacote `core` expõe apenas os contratos centrais e o Kernel. Regras de domínio
ficam fora daqui por definição arquitetural.
"""

from huli.core.contracts import InvalidKernelInput, KernelRequest, KernelResponse
from huli.core.kernel import Kernel

__all__ = [
    "InvalidKernelInput",
    "Kernel",
    "KernelRequest",
    "KernelResponse",
]
