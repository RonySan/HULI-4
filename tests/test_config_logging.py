"""Testes de configuração e logging da fundação."""

from io import StringIO
from pathlib import Path

import pytest

from huli.infrastructure import Settings, configure_logging, load_settings


def test_load_settings_uses_safe_defaults() -> None:
    settings = load_settings({})
    assert settings.environment == "development"
    assert settings.log_level == "INFO"
    assert settings.data_dir == Path("data")


def test_load_settings_reads_environment_values() -> None:
    settings = load_settings(
        {
            "HULI_ENV": "test",
            "HULI_LOG_LEVEL": "debug",
            "HULI_DATA_DIR": "runtime-data",
        }
    )
    assert settings.environment == "test"
    assert settings.log_level == "DEBUG"
    assert settings.data_dir == Path("runtime-data")


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
