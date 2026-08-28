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
            "HULI_JOURNAL_LOCK_MINUTES": "7",
            "HULI_VOICE_AUTO_SPEAK": "sim",
            "HULI_VOICE_INPUT_TIMEOUT": "12",
            "HULI_VOICE_LANGUAGE": "pt-BR",
            "HULI_VOICE_RATE": "1",
            "HULI_VOICE_VOLUME": "90",
        }
    )

    assert settings.environment == "test"
    assert settings.log_level == "DEBUG"
    assert settings.data_dir == tmp_path
    assert settings.api_host == "0.0.0.0"
    assert settings.api_port == 9000
    assert settings.session_hours == 12
    assert settings.max_input_chars == 2000
    assert settings.journal_lock_minutes == 7
    assert settings.voice_auto_speak is True
    assert settings.voice_input_timeout == 12
    assert settings.voice_language == "pt-BR"
    assert settings.voice_rate == 1
    assert settings.voice_volume == 90
    assert settings.database_path == tmp_path / "huli.db"
    assert settings.backup_dir == tmp_path / "backups"


def test_load_settings_rejects_invalid_api_port() -> None:
    with pytest.raises(ValueError, match="HULI_API_PORT"):
        load_settings({"HULI_API_PORT": "99999"})


def test_load_settings_rejects_invalid_journal_lock() -> None:
    with pytest.raises(ValueError, match="HULI_JOURNAL_LOCK_MINUTES"):
        load_settings({"HULI_JOURNAL_LOCK_MINUTES": "0"})


def test_load_settings_rejects_invalid_voice_values() -> None:
    with pytest.raises(ValueError, match="HULI_VOICE_INPUT_TIMEOUT"):
        load_settings({"HULI_VOICE_INPUT_TIMEOUT": "1"})
    with pytest.raises(ValueError, match="HULI_VOICE_AUTO_SPEAK"):
        load_settings({"HULI_VOICE_AUTO_SPEAK": "talvez"})
    with pytest.raises(ValueError, match="HULI_VOICE_LANGUAGE"):
        load_settings({"HULI_VOICE_LANGUAGE": "português brasileiro"})
