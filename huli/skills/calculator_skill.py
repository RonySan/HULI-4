"""Skill de calculos locais."""

from __future__ import annotations

from huli.brain.calculator import CalculatorError, calculate, format_result
from huli.core.contracts import KernelRequest, KernelResponse


class CalculatorSkill:
    name = "calculator"
    intents = ("calculator.query",)

    def can_handle(self, request: KernelRequest) -> bool:
        return str(request.metadata.get("intent", "")) in self.intents

    def handle(self, request: KernelRequest) -> KernelResponse:
        try:
            result = calculate(request.text)
        except CalculatorError as exc:
            return KernelResponse(
                request_id=request.request_id,
                text=str(exc),
                handled_by=self.name,
                ok=False,
            )
        return KernelResponse(
            request_id=request.request_id,
            text=f"O resultado é {format_result(result)}.",
            handled_by=self.name,
        )
