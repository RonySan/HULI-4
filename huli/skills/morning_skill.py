"""Resumo matinal pessoal da Huli."""

from __future__ import annotations

from datetime import datetime

from huli.brain.agenda import AgendaService
from huli.brain.weather import OpenMeteoWeatherService, WeatherError
from huli.core.contracts import KernelRequest, KernelResponse


class MorningBriefingSkill:
    name = "morning-briefing"
    intents = ("morning.briefing",)

    def __init__(self, agenda: AgendaService, weather: OpenMeteoWeatherService, *, max_appointments: int = 5) -> None:
        self.agenda = agenda
        self.weather = weather
        self.max_appointments = max(1, max_appointments)

    def can_handle(self, request: KernelRequest) -> bool:
        return str(request.metadata.get("intent", "")) in self.intents

    def handle(self, request: KernelRequest) -> KernelResponse:
        if str(request.metadata.get("role", "guest")) != "owner":
            return self._response(request, "Bom dia. Para consultar sua agenda pessoal, entre como proprietário.", ok=False)

        now = self.agenda.now()
        appointments = self.agenda.today(now)
        parts = [f"Bom dia, senhor. Agora são {now.strftime('%H:%M')}."]
        if not appointments:
            parts.append("Sua agenda de hoje está livre.")
        else:
            visible = appointments[: self.max_appointments]
            schedule = "; ".join(self._format_appointment(item.start_at, item.title) for item in visible)
            total = len(appointments)
            label = "compromisso" if total == 1 else "compromissos"
            parts.append(f"Hoje você tem {total} {label}: {schedule}.")
            hidden = total - len(visible)
            if hidden:
                parts.append(f"Há mais {hidden} na agenda de hoje.")

        try:
            weather = self.weather.current_and_today()
        except WeatherError:
            parts.append("Não consegui consultar o clima agora.")
        else:
            parts.append(
                f"Em {weather.location}, agora faz {weather.temperature:.0f} graus, com {weather.condition}. "
                f"A máxima será de {weather.maximum_temperature:.0f} e a mínima de {weather.minimum_temperature:.0f} graus, "
                f"com até {weather.rain_probability}% de chance de chuva."
            )
            parts.append(f"Minha sugestão: {weather.clothing_suggestion}")
        return self._response(request, " ".join(parts))

    def _format_appointment(self, start_at: str, title: str) -> str:
        local = datetime.fromisoformat(start_at).astimezone(self.agenda.timezone)
        return f"{local.strftime('%H:%M')} — {title}"

    def _response(self, request: KernelRequest, text: str, *, ok: bool = True) -> KernelResponse:
        return KernelResponse(request_id=request.request_id, text=text, handled_by=self.name, ok=ok)


__all__ = ["MorningBriefingSkill"]
