"""Skill para criar, consultar e cancelar temporizadores."""

from __future__ import annotations

from huli.brain.timers import TimerService, extract_timer_identifier, format_duration, parse_timer_request
from huli.core.contracts import KernelRequest, KernelResponse


class TimerSkill:
    name = "timers"
    intents = ("timer.create", "timer.list", "timer.cancel")

    def __init__(self, timers: TimerService) -> None:
        self.timers = timers

    def can_handle(self, request: KernelRequest) -> bool:
        return str(request.metadata.get("intent", "")) in self.intents

    def handle(self, request: KernelRequest) -> KernelResponse:
        intent = str(request.metadata.get("intent", ""))
        if intent == "timer.create":
            try:
                duration, label = parse_timer_request(request.text)
                timer = self.timers.create(duration, label)
            except ValueError as exc:
                return self._response(request, str(exc), ok=False)
            return self._response(
                request,
                f"Temporizador #{timer.id} iniciado por {format_duration(duration)}: {label}.",
            )
        if intent == "timer.list":
            active = self.timers.active()
            if not active:
                return self._response(request, "Não há temporizadores ativos.")
            lines = [f"Você tem {len(active)} temporizador(es) ativo(s):"]
            lines.extend(
                f"- #{timer.id} {timer.label} — faltam {format_duration(remaining)}"
                for timer, remaining in active
            )
            return self._response(request, "\n".join(lines))
        if intent == "timer.cancel":
            identifier = extract_timer_identifier(request.text)
            timer = self.timers.cancel(identifier)
            if timer is None:
                return self._response(request, "Não encontrei esse temporizador ativo.", ok=False)
            return self._response(request, f"Temporizador #{timer.id} cancelado: {timer.label}.")
        return self._response(request, "Não consegui executar essa ação do temporizador.", ok=False)

    def _response(self, request: KernelRequest, text: str, *, ok: bool = True) -> KernelResponse:
        return KernelResponse(request_id=request.request_id, text=text, handled_by=self.name, ok=ok)
