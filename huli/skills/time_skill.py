"""Consulta local de horário."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from huli.core.contracts import KernelRequest, KernelResponse


class TimeSkill:
    name = "time"
    intents = ("time.query", "date.query")

    _WEEKDAYS = (
        "segunda-feira",
        "terça-feira",
        "quarta-feira",
        "quinta-feira",
        "sexta-feira",
        "sábado",
        "domingo",
    )
    _MONTHS = (
        "janeiro",
        "fevereiro",
        "março",
        "abril",
        "maio",
        "junho",
        "julho",
        "agosto",
        "setembro",
        "outubro",
        "novembro",
        "dezembro",
    )

    def __init__(self, timezone_name: str) -> None:
        self.timezone = ZoneInfo(timezone_name)

    def can_handle(self, request: KernelRequest) -> bool:
        return str(request.metadata.get("intent", "")) in self.intents

    def handle(self, request: KernelRequest) -> KernelResponse:
        now = datetime.now(self.timezone)
        intent = str(request.metadata.get("intent") or "time.query")
        if intent == "date.query":
            weekday = self._WEEKDAYS[now.weekday()]
            month = self._MONTHS[now.month - 1]
            text = f"Hoje é {weekday}, {now.day} de {month} de {now.year}."
        else:
            text = f"Agora são {now.strftime('%H:%M')} de {now.strftime('%d/%m/%Y')}."
        return KernelResponse(
            request_id=request.request_id,
            text=text,
            handled_by=self.name,
        )
