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


def load_settings(source: Mapping[str, str] | None = None) -> Settings:
    """Carrega configurações de variáveis de ambiente sem dependências externas."""
    values = source if source is not None else os.environ

    environment = values.get("HULI_ENV", "development").strip() or "development"
    log_level = (values.get("HULI_LOG_LEVEL", "INFO").strip() or "INFO").upper()
    if log_level not in _VALID_LOG_LEVELS:
        allowed = ", ".join(sorted(_VALID_LOG_LEVELS))
        raise ValueError(f"HULI_LOG_LEVEL inválido. Use um de: {allowed}.")

    raw_data_dir = values.get("HULI_DATA_DIR", "data").strip() or "data"
    return Settings(
        environment=environment,
        log_level=log_level,
        data_dir=Path(raw_data_dir).expanduser(),
    )
