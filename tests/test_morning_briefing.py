"""Testes da saudação matinal, clima e recomendação de roupa."""

from __future__ import annotations

from datetime import datetime
from io import BytesIO
import json
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from huli.brain.weather import (
    OpenMeteoWeatherService,
    WeatherError,
    WeatherSnapshot,
    suggest_clothing,
)
from huli.core import KernelRequest
from huli.skills import MorningBriefingSkill
from tools.morning_alarm import morning_panel_environment


class _Agenda:
    timezone = ZoneInfo("America/Sao_Paulo")

    def __init__(self, appointments=()) -> None:
        self.appointments = tuple(appointments)

    def now(self) -> datetime:
        return datetime(2026, 9, 2, 5, 52, tzinfo=self.timezone)

    def today(self, now: datetime):
        return self.appointments


class _Weather:
    def current_and_today(self) -> WeatherSnapshot:
        return WeatherSnapshot(
            location="São Paulo, São Paulo",
            temperature=15,
            apparent_temperature=14,
            minimum_temperature=12,
            maximum_temperature=23,
            rain_probability=60,
            weather_code=61,
        )


class _OfflineWeather:
    def current_and_today(self) -> WeatherSnapshot:
        raise WeatherError("offline")


def _owner_request() -> KernelRequest:
    return KernelRequest.from_text(
        "bom dia",
        metadata={"intent": "morning.briefing", "role": "owner", "username": "rony"},
    )


def test_morning_briefing_is_direct_and_uses_only_today_agenda() -> None:
    appointment = SimpleNamespace(
        start_at="2026-09-02T08:30:00-03:00", title="Reunião da equipe"
    )
    response = MorningBriefingSkill(_Agenda((appointment,)), _Weather()).handle(
        _owner_request()
    )

    assert response.ok is True
    assert response.handled_by == "morning-briefing"
    assert "Bom dia, senhor. Agora são 05:52." in response.text
    assert "Hoje você tem 1 compromisso: 08:30 — Reunião da equipe." in response.text
    assert "São Paulo" in response.text
    assert "leve guarda-chuva" in response.text


def test_weather_failure_does_not_hide_time_or_agenda() -> None:
    response = MorningBriefingSkill(_Agenda(), _OfflineWeather()).handle(
        _owner_request()
    )

    assert response.ok is True
    assert "Agora são 05:52" in response.text
    assert "agenda de hoje está livre" in response.text
    assert "Não consegui consultar o clima agora" in response.text


def test_morning_briefing_protects_private_agenda_from_guest() -> None:
    request = KernelRequest.from_text(
        "bom dia", metadata={"intent": "morning.briefing", "role": "guest"}
    )
    response = MorningBriefingSkill(_Agenda(), _Weather()).handle(request)

    assert response.ok is False
    assert "entre como proprietário" in response.text


def test_open_meteo_client_parses_current_and_daily_values() -> None:
    payload = {
        "current": {
            "temperature_2m": 21.4,
            "apparent_temperature": 20.2,
            "weather_code": 2,
        },
        "daily": {
            "temperature_2m_max": [26.0],
            "temperature_2m_min": [16.0],
            "precipitation_probability_max": [20],
            "weather_code": [2],
        },
    }

    class _Response(BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.close()

    seen: dict[str, object] = {}

    def opener(url: str, *, timeout: int):
        seen.update(url=url, timeout=timeout)
        return _Response(json.dumps(payload).encode("utf-8"))

    service = OpenMeteoWeatherService(
        location="São Paulo",
        latitude=-23.55,
        longitude=-46.63,
        timezone_name="America/Sao_Paulo",
        opener=opener,
    )
    result = service.current_and_today()

    assert result.temperature == 21.4
    assert result.condition == "parcialmente nublado"
    assert "forecast_days=1" in str(seen["url"])
    assert seen["timeout"] == 5


def test_clothing_suggestion_uses_temperature_and_rain() -> None:
    snapshot = WeatherSnapshot("São Paulo", 30, 31, 21, 32, 70, 80)
    suggestion = suggest_clothing(snapshot)
    assert "roupa leve" in suggestion
    assert "guarda-chuva" in suggestion


def test_alarm_opens_panel_with_listening_and_speech_enabled() -> None:
    environment = morning_panel_environment()
    assert environment["HULI_VOICE_WAKE_ENABLED"] == "true"
    assert environment["HULI_VOICE_AUTO_SPEAK"] == "true"
