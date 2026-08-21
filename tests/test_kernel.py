"""Testes do Kernel mínimo da Huli."""

import pytest

from huli.core import InvalidKernelInput, Kernel, KernelResponse
from huli.core.contracts import KernelRequest


def test_kernel_receives_valid_message() -> None:
    kernel = Kernel()

    response = kernel.process("  teste de mensagem  ")

    assert response.ok is True
    assert response.handled_by == "kernel"
    assert response.request_id
    assert "Mensagem recebida" in response.text


def test_kernel_rejects_empty_input() -> None:
    kernel = Kernel()

    with pytest.raises(InvalidKernelInput):
        kernel.process("   ")


def test_kernel_rejects_non_text_input() -> None:
    kernel = Kernel()

    with pytest.raises(InvalidKernelInput):
        kernel.process(None)  # type: ignore[arg-type]


def test_kernel_delegates_to_injected_handler() -> None:
    class StubHandler:
        def handle(self, request: KernelRequest) -> KernelResponse:
            return KernelResponse(
                request_id=request.request_id,
                text=f"eco: {request.text}",
                handled_by="stub",
            )

    kernel = Kernel(handler=StubHandler())

    response = kernel.process("olá")

    assert response.text == "eco: olá"
    assert response.handled_by == "stub"


def test_kernel_rejects_response_with_wrong_request_id() -> None:
    class InvalidHandler:
        def handle(self, request: KernelRequest) -> KernelResponse:
            return KernelResponse(
                request_id="request-incorreto",
                text="resposta inválida",
                handled_by="invalid",
            )

    kernel = Kernel(handler=InvalidHandler())

    with pytest.raises(RuntimeError, match="request_id inválido"):
        kernel.process("teste")
