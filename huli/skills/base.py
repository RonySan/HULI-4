"""Contratos fundamentais para Skills da Huli."""

from __future__ import annotations

from typing import Protocol

from huli.core.contracts import KernelRequest, KernelResponse


class Skill(Protocol):
    """Contrato mínimo de uma capacidade especializada."""

    @property
    def name(self) -> str:
        """Nome técnico único da Skill."""

    def can_handle(self, request: KernelRequest) -> bool:
        """Indica se a Skill consegue atender a requisição."""

    def handle(self, request: KernelRequest) -> KernelResponse:
        """Executa a capacidade e devolve uma resposta estruturada."""
