"""Consulta local de horário."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from huli.core.contracts import KernelRequest, KernelResponse


class TimeSkill:
    name = "time"
    intents = ("time.query",)

    def __init__(self, timezone_name: str) -> None:
        self.timezone = ZoneInfo(timezone_name)

    def can_handle(self, request: KernelRequest) -> bool:
        return str(request.metadata.get("intent", "")) in self.intents

    def handle(self, request: KernelRequest) -> KernelResponse:
        now = datetime.now(self.timezone)
        return KernelResponse(request_id=request.request_id, text=f"Agora são {now.strftime('%H:%M')} de {now.strftime('%d/%m/%Y')}.", handled_by=self.name)
