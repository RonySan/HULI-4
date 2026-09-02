"""Testes de configuração e logging da fundação."""

from io import StringIO

import pytest

from huli.infrastructure import Settings, configure_logging, load_settings
from huli.infrastructure.config import APP_ROOT


def test_load_settings_uses_safe_defaults() -> None:
    settings = load_settings({})
    assert settings.environment == "development"
    assert settings.log_level == "INFO"
    assert settings.data_dir == APP_ROOT / "data"
    assert settings.voice_wake_enabled is False
    assert settings.voice_wake_cycle_timeout == 30


def test_load_settings_reads_environment_values() -> None:
    settings = load_settings(
        {
            "HULI_ENV": "test",
            "HULI_LOG_LEVEL": "debug",
            "HULI_DATA_DIR": "runtime-data",
            "HULI_VOICE_WAKE_ENABLED": "sim",
            "HULI_VOICE_WAKE_CYCLE_TIMEOUT": "5",
        }
    )
    assert settings.environment == "test"
    assert settings.log_level == "DEBUG"
    assert settings.data_dir == APP_ROOT / "runtime-data"
    assert settings.voice_wake_enabled is True
    assert settings.voice_wake_cycle_timeout == 5


def test_load_settings_rejects_invalid_log_level() -> None:
    with pytest.raises(ValueError):
        load_settings({"HULI_LOG_LEVEL": "barulho"})


def test_configure_logging_writes_structured_line() -> None:
    stream = StringIO()
    logger = configure_logging(Settings(log_level="INFO"), stream=stream)
    logger.info("foundation_ready module=%s", "logging")

    output = stream.getvalue()
    assert "level=INFO" in output
    assert "logger=huli" in output
    assert "foundation_ready module=logging" in output
