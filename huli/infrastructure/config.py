"""Configuração centralizada da Huli."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping
import os
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

_VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


@dataclass(frozen=True, slots=True)
class Settings:
    environment: str = "development"
    log_level: str = "INFO"
    data_dir: Path = Path("data")
    api_host: str = "127.0.0.1"
    api_port: int = 8765
    session_hours: int = 24 * 7
    max_input_chars: int = 10_000
    timezone: str = "America/Sao_Paulo"
    context_turns: int = 20
    journal_lock_minutes: int = 15
    voice_auto_speak: bool = False
    voice_input_timeout: int = 8
    voice_language: str = "pt-BR"
    voice_rate: int = 0
    voice_volume: int = 100

    @property
    def database_path(self) -> Path:
        return self.data_dir / "huli.db"

    @property
    def backup_dir(self) -> Path:
        return self.data_dir / "backups"


def load_settings(source: Mapping[str, str] | None = None) -> Settings:
    values = source if source is not None else os.environ
    environment = values.get("HULI_ENV", "development").strip() or "development"
    log_level = (values.get("HULI_LOG_LEVEL", "INFO").strip() or "INFO").upper()
    if log_level not in _VALID_LOG_LEVELS:
        raise ValueError(f"HULI_LOG_LEVEL inválido. Use um de: {', '.join(sorted(_VALID_LOG_LEVELS))}.")
    raw_data_dir = values.get("HULI_DATA_DIR", "data").strip() or "data"
    api_host = values.get("HULI_API_HOST", "127.0.0.1").strip() or "127.0.0.1"
    api_port = _read_int(values, "HULI_API_PORT", 8765, minimum=1, maximum=65535)
    session_hours = _read_int(values, "HULI_SESSION_HOURS", 24 * 7, minimum=1, maximum=24 * 365)
    max_input_chars = _read_int(values, "HULI_MAX_INPUT_CHARS", 10_000, minimum=100, maximum=1_000_000)
    timezone_name = values.get("HULI_TIMEZONE", "America/Sao_Paulo").strip() or "America/Sao_Paulo"
    try:
        ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"HULI_TIMEZONE inválido: {timezone_name}.") from exc
    context_turns = _read_int(values, "HULI_CONTEXT_TURNS", 20, minimum=1, maximum=200)
    journal_lock_minutes = _read_int(
        values,
        "HULI_JOURNAL_LOCK_MINUTES",
        15,
        minimum=1,
        maximum=24 * 60,
    )
    voice_auto_speak = _read_bool(values, "HULI_VOICE_AUTO_SPEAK", False)
    voice_input_timeout = _read_int(
        values,
        "HULI_VOICE_INPUT_TIMEOUT",
        8,
        minimum=2,
        maximum=60,
    )
    voice_language = values.get("HULI_VOICE_LANGUAGE", "pt-BR").strip() or "pt-BR"
    if not re.fullmatch(r"[A-Za-z]{2,3}(?:-[A-Za-z]{2,4})?", voice_language):
        raise ValueError("HULI_VOICE_LANGUAGE deve usar um código como pt-BR.")
    voice_rate = _read_int(values, "HULI_VOICE_RATE", 0, minimum=-10, maximum=10)
    voice_volume = _read_int(values, "HULI_VOICE_VOLUME", 100, minimum=0, maximum=100)
    return Settings(
        environment=environment,
        log_level=log_level,
        data_dir=Path(raw_data_dir).expanduser(),
        api_host=api_host,
        api_port=api_port,
        session_hours=session_hours,
        max_input_chars=max_input_chars,
        timezone=timezone_name,
        context_turns=context_turns,
        journal_lock_minutes=journal_lock_minutes,
        voice_auto_speak=voice_auto_speak,
        voice_input_timeout=voice_input_timeout,
        voice_language=voice_language,
        voice_rate=voice_rate,
        voice_volume=voice_volume,
    )


def _read_int(values: Mapping[str, str], key: str, default: int, *, minimum: int, maximum: int) -> int:
    raw = values.get(key)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{key} precisa ser um número inteiro.") from exc
    if value < minimum or value > maximum:
        raise ValueError(f"{key} precisa estar entre {minimum} e {maximum}.")
    return value


def _read_bool(values: Mapping[str, str], key: str, default: bool) -> bool:
    raw = values.get(key)
    if raw is None or not raw.strip():
        return default
    normalized = raw.strip().casefold()
    if normalized in {"1", "true", "sim", "yes", "on", "ligado"}:
        return True
    if normalized in {"0", "false", "nao", "não", "no", "off", "desligado"}:
        return False
    raise ValueError(f"{key} precisa ser true/false ou sim/não.")
