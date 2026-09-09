"""Inicialização opcional da Huli com a sessão do Windows."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
import sys
from typing import Protocol


_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_VALUE_NAME = "Huli"


class AutoStartError(RuntimeError):
    """Falha compreensível ao configurar a inicialização automática."""


class RegistryBackend(Protocol):
    def read(self, key: str, name: str) -> str | None: ...

    def write(self, key: str, name: str, value: str) -> None: ...

    def delete(self, key: str, name: str) -> None: ...


class _WindowsRegistry:
    def read(self, key: str, name: str) -> str | None:
        import winreg

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as handle:
                value, _kind = winreg.QueryValueEx(handle, name)
        except FileNotFoundError:
            return None
        return str(value)

    def write(self, key: str, name: str, value: str) -> None:
        import winreg

        with winreg.CreateKeyEx(
            winreg.HKEY_CURRENT_USER,
            key,
            0,
            winreg.KEY_SET_VALUE,
        ) as handle:
            winreg.SetValueEx(handle, name, 0, winreg.REG_SZ, value)

    def delete(self, key: str, name: str) -> None:
        import winreg

        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                key,
                0,
                winreg.KEY_SET_VALUE,
            ) as handle:
                winreg.DeleteValue(handle, name)
        except FileNotFoundError:
            return


@dataclass(slots=True)
class WindowsAutoStart:
    """Gerencia a entrada da Huli em HKCU, sem exigir administrador."""

    app_root: Path
    backend: RegistryBackend | None = None

    def __post_init__(self) -> None:
        self.app_root = self.app_root.resolve()
        if self.backend is None and sys.platform == "win32":
            self.backend = _WindowsRegistry()

    @property
    def supported(self) -> bool:
        return self.backend is not None

    @property
    def pythonw_path(self) -> Path:
        return self.app_root / ".venv" / "Scripts" / "pythonw.exe"

    @property
    def panel_path(self) -> Path:
        return self.app_root / "painel.py"

    @property
    def command(self) -> str:
        return subprocess.list2cmdline(
            [
                str(self.pythonw_path),
                str(self.panel_path),
                "--resident",
                "--minimized",
                "--startup",
            ]
        )

    def is_enabled(self) -> bool:
        backend = self._require_backend()
        current = backend.read(_RUN_KEY, _VALUE_NAME)
        return current == self.command

    def enable(self) -> None:
        backend = self._require_backend()
        missing = [path for path in (self.pythonw_path, self.panel_path) if not path.is_file()]
        if missing:
            raise AutoStartError(
                "Não encontrei o ambiente completo da Huli: "
                + ", ".join(str(path) for path in missing)
            )
        try:
            backend.write(_RUN_KEY, _VALUE_NAME, self.command)
        except OSError as exc:
            raise AutoStartError(f"O Windows recusou a configuração: {exc}") from exc

    def disable(self) -> None:
        backend = self._require_backend()
        try:
            backend.delete(_RUN_KEY, _VALUE_NAME)
        except OSError as exc:
            raise AutoStartError(f"O Windows recusou a alteração: {exc}") from exc

    def _require_backend(self) -> RegistryBackend:
        if self.backend is None:
            raise AutoStartError("A inicialização automática só está disponível no Windows.")
        return self.backend
