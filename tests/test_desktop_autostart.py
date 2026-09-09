"""Testes do início opcional com o Windows."""

from pathlib import Path

import pytest

from huli.desktop.autostart import AutoStartError, WindowsAutoStart


class FakeRegistry:
    def __init__(self) -> None:
        self.values: dict[tuple[str, str], str] = {}

    def read(self, key: str, name: str) -> str | None:
        return self.values.get((key, name))

    def write(self, key: str, name: str, value: str) -> None:
        self.values[(key, name)] = value

    def delete(self, key: str, name: str) -> None:
        self.values.pop((key, name), None)


def _installation(tmp_path: Path) -> tuple[WindowsAutoStart, FakeRegistry]:
    (tmp_path / ".venv" / "Scripts").mkdir(parents=True)
    (tmp_path / ".venv" / "Scripts" / "pythonw.exe").touch()
    (tmp_path / "painel.py").touch()
    registry = FakeRegistry()
    return WindowsAutoStart(tmp_path, registry), registry


def test_autostart_round_trip_uses_resident_minimized_command(tmp_path: Path) -> None:
    autostart, _registry = _installation(tmp_path)

    assert not autostart.is_enabled()
    autostart.enable()
    assert autostart.is_enabled()
    assert "pythonw.exe" in autostart.command
    assert "--resident" in autostart.command
    assert "--minimized" in autostart.command
    assert "--startup" in autostart.command

    autostart.disable()
    assert not autostart.is_enabled()


def test_autostart_refuses_incomplete_installation(tmp_path: Path) -> None:
    autostart = WindowsAutoStart(tmp_path, FakeRegistry())

    with pytest.raises(AutoStartError, match="ambiente completo"):
        autostart.enable()
