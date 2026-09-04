"""Resposta curta sobre a saude do computador local."""

from __future__ import annotations

from huli.core.contracts import KernelRequest, KernelResponse
from huli.infrastructure.system_health import SystemHealthMonitor, SystemHealthSnapshot


class SystemHealthSkill:
    name = "computer-health"
    intents = ("computer.health",)

    def __init__(self, monitor: SystemHealthMonitor) -> None:
        self.monitor = monitor

    def can_handle(self, request: KernelRequest) -> bool:
        return str(request.metadata.get("intent", "")) in self.intents

    def handle(self, request: KernelRequest) -> KernelResponse:
        try:
            snapshot = self.monitor.snapshot()
        except OSError:
            return KernelResponse(
                request_id=request.request_id,
                text="Não consegui ler os indicadores do computador agora.",
                handled_by=self.name,
                ok=False,
            )
        return KernelResponse(
            request_id=request.request_id,
            text=self._describe(snapshot),
            handled_by=self.name,
        )

    @staticmethod
    def _describe(snapshot: SystemHealthSnapshot) -> str:
        values = [
            value
            for value in (
                snapshot.cpu_percent,
                snapshot.memory_percent,
                snapshot.disk_percent,
            )
            if value is not None
        ]
        peak = max(values, default=0)
        state = "precisa de atenção" if peak >= 90 else "está um pouco carregado" if peak >= 80 else "está normal"
        parts: list[str] = []
        if snapshot.cpu_percent is not None:
            parts.append(f"processador {snapshot.cpu_percent:.0f}%")
        if snapshot.memory_percent is not None:
            parts.append(f"memória {snapshot.memory_percent:.0f}%")
        parts.append(f"disco {snapshot.disk_name} {snapshot.disk_percent:.0f}%")
        if snapshot.battery_percent is not None:
            source = "carregando" if snapshot.battery_plugged else "na bateria"
            parts.append(f"bateria {snapshot.battery_percent}% ({source})")
        if snapshot.uptime_seconds is not None:
            parts.append(f"ligado há {SystemHealthSkill._duration(snapshot.uptime_seconds)}")
        warning = " Pouco espaço em disco." if snapshot.disk_percent >= 90 else ""
        return f"Seu computador {state}: {', '.join(parts)}.{warning}"

    @staticmethod
    def _duration(seconds: float) -> str:
        total_minutes = max(0, int(seconds // 60))
        days, remaining = divmod(total_minutes, 1440)
        hours, minutes = divmod(remaining, 60)
        if days:
            return f"{days}d {hours}h"
        if hours:
            return f"{hours}h {minutes}min"
        return f"{minutes}min"
