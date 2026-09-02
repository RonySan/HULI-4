"""Consulta meteorológica enxuta para a rotina matinal da Huli."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Callable
from urllib.parse import urlencode
from urllib.request import urlopen


class WeatherError(RuntimeError):
    """Falha controlada ao consultar ou interpretar a previsão."""


@dataclass(frozen=True, slots=True)
class WeatherSnapshot:
    location: str
    temperature: float
    apparent_temperature: float
    minimum_temperature: float
    maximum_temperature: float
    rain_probability: int
    weather_code: int

    @property
    def condition(self) -> str:
        return describe_weather_code(self.weather_code)

    @property
    def clothing_suggestion(self) -> str:
        return suggest_clothing(self)


class OpenMeteoWeatherService:
    """Cliente sem chave e sem dependência externa para o Open-Meteo."""

    endpoint = "https://api.open-meteo.com/v1/forecast"

    def __init__(
        self,
        *,
        location: str,
        latitude: float,
        longitude: float,
        timezone_name: str,
        timeout_seconds: int = 5,
        opener: Callable[..., object] = urlopen,
    ) -> None:
        self.location = location
        self.latitude = latitude
        self.longitude = longitude
        self.timezone_name = timezone_name
        self.timeout_seconds = timeout_seconds
        self._opener = opener

    def current_and_today(self) -> WeatherSnapshot:
        query = urlencode(
            {
                "latitude": self.latitude,
                "longitude": self.longitude,
                "current": "temperature_2m,apparent_temperature,weather_code",
                "daily": (
                    "temperature_2m_max,temperature_2m_min,"
                    "precipitation_probability_max,weather_code"
                ),
                "timezone": self.timezone_name,
                "forecast_days": 1,
            }
        )
        try:
            with self._opener(
                f"{self.endpoint}?{query}", timeout=self.timeout_seconds
            ) as response:
                payload = json.loads(response.read().decode("utf-8"))
            current = payload["current"]
            daily = payload["daily"]
            return WeatherSnapshot(
                location=self.location,
                temperature=float(current["temperature_2m"]),
                apparent_temperature=float(current["apparent_temperature"]),
                minimum_temperature=float(daily["temperature_2m_min"][0]),
                maximum_temperature=float(daily["temperature_2m_max"][0]),
                rain_probability=int(daily["precipitation_probability_max"][0]),
                weather_code=int(current.get("weather_code", daily["weather_code"][0])),
            )
        except (KeyError, IndexError, TypeError, ValueError, OSError) as exc:
            raise WeatherError("Não consegui consultar o clima agora.") from exc


def describe_weather_code(code: int) -> str:
    if code == 0:
        return "céu limpo"
    if code in {1, 2}:
        return "parcialmente nublado"
    if code == 3:
        return "nublado"
    if code in {45, 48}:
        return "neblina"
    if 51 <= code <= 57:
        return "garoa"
    if 61 <= code <= 67:
        return "chuva"
    if 71 <= code <= 77:
        return "neve"
    if 80 <= code <= 82:
        return "pancadas de chuva"
    if code in {85, 86}:
        return "pancadas de neve"
    if 95 <= code <= 99:
        return "tempestade"
    return "tempo variável"


def suggest_clothing(weather: WeatherSnapshot) -> str:
    reference = min(weather.temperature, weather.minimum_temperature)
    if reference <= 12:
        suggestion = "use casaco, calça e calçado fechado"
    elif reference <= 18:
        suggestion = "uma jaqueta leve e calça vão bem"
    elif weather.maximum_temperature >= 28:
        suggestion = "prefira roupa leve e fresca"
    else:
        suggestion = "roupa leve deve ficar confortável"

    if weather.rain_probability >= 40 or weather.weather_code in range(51, 100):
        suggestion += "; leve guarda-chuva"
    return suggestion + "."


__all__ = [
    "OpenMeteoWeatherService",
    "WeatherError",
    "WeatherSnapshot",
    "describe_weather_code",
    "suggest_clothing",
]
