"""Testes das configurações de runtime."""

from pathlib import Path

import pytest

from huli.infrastructure import load_settings


def test_load_settings_reads_runtime_values(tmp_path: Path) -> None:
    settings = load_settings(
        {
            "HULI_ENV": "test",
            "HULI_LOG_LEVEL": "debug",
            "HULI_DATA_DIR": str(tmp_path),
            "HULI_API_HOST": "0.0.0.0",
            "HULI_API_PORT": "9000",
            "HULI_SESSION_HOURS": "12",
            "HULI_MAX_INPUT_CHARS": "2000",
        }
    )

    assert settings.environment == "test"
    assert settings.log_level == "DEBUG"
    assert settings.data_dir == tmp_path
    assert settings.api_host == "0.0.0.0"
    assert settings.api_port == 9000
    assert settings.session_hours == 12
    assert settings.max_input_chars == 2000
    assert settings.database_path == tmp_path / "huli.db"


def test_load_settings_rejects_invalid_api_port() -> None:
    with pytest.raises(ValueError, match="HULI_API_PORT"):
        load_settings({"HULI_API_PORT": "99999"})
