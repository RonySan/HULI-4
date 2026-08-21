"""Contratos fundamentais usados pelo Kernel da Huli.

Este módulo contém apenas estruturas estáveis de entrada e saída. Ele não conhece
Skills, memória, IA, banco de dados ou interfaces de usuário.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol
from uuid import uuid4


class InvalidKernelInput(ValueError):
    """Erro lançado quando o Kernel recebe uma entrada inválida."""


@dataclass(frozen=True, slots=True)
class KernelRequest:
    """Mensagem normalizada recebida pelo Kernel."""

    text: str
    request_id: str = field(default_factory=lambda: uuid4().hex)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def from_text(cls, text: str) -> "KernelRequest":
        """Cria uma requisição válida a partir de texto bruto."""
        if not isinstance(text, str):
            raise InvalidKernelInput("A entrada do Kernel precisa ser texto.")

        normalized = text.strip()
        if not normalized:
            raise InvalidKernelInput("A entrada do Kernel não pode estar vazia.")

        return cls(text=normalized)


@dataclass(frozen=True, slots=True)
class KernelResponse:
    """Resposta estruturada produzida pelo Kernel."""

    request_id: str
    text: str
    handled_by: str
    ok: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class KernelHandler(Protocol):
    """Contrato que futuros componentes poderão implementar para atender mensagens."""

    def handle(self, request: KernelRequest) -> KernelResponse:
        """Processa uma requisição e devolve uma resposta estruturada."""
