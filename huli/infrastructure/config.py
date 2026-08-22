"""Configuração centralizada da Huli."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping
import os


_VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


@dataclass(frozen=True, slots=True)
class Settings:
    """Configurações imutáveis carregadas na inicialização."""

    environment: str = "development"
    log_level: str = "INFO"
    data_dir: Path = Path("data")
    api_host: str = "127.0.0.1"
    api_port: int = 8765
    session_hours: int = 24 * 7
    max_input_chars: int = 10_000

    @property
    def database_path(self) -> Path:
        return self.data_dir / "huli.db"


def load_settings(source: Mapping[str, str] | None = None) -> Settings:
    """Carrega configurações de variáveis de ambiente sem estado global oculto."""
    values = source if source is not None else os.environ

    environment = values.get("HULI_ENV", "development").strip() or "development"
    log_level = (values.get("HULI_LOG_LEVEL", "INFO").strip() or "INFO").upper()
    if log_level not in _VALID_LOG_LEVELS:
        allowed = ", ".join(sorted(_VALID_LOG_LEVELS))
        raise ValueError(f"HULI_LOG_LEVEL inválido. Use um de: {allowed}.")

    raw_data_dir = values.get("HULI_DATA_DIR", "data").strip() or "data"
    api_host = values.get("HULI_API_HOST", "127.0.0.1").strip() or "127.0.0.1"
    api_port = _read_int(values, "HULI_API_PORT", 8765, minimum=1, maximum=65535)
    session_hours = _read_int(values, "HULI_SESSION_HOURS", 24 * 7, minimum=1, maximum=24 * 365)
    max_input_chars = _read_int(
        values,
        "HULI_MAX_INPUT_CHARS",
        10_000,
        minimum=100,
        maximum=1_000_000,
    )

    return Settings(
        environment=environment,
        log_level=log_level,
        data_dir=Path(raw_data_dir).expanduser(),
        api_host=api_host,
        api_port=api_port,
        session_hours=session_hours,
        max_input_chars=max_input_chars,
    )


def _read_int(
    values: Mapping[str, str],
    key: str,
    default: int,
    *,
    minimum: int,
    maximum: int,
) -> int:
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
