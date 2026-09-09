"""Integrações locais do modo residente da Huli."""

from huli.desktop.autostart import AutoStartError, WindowsAutoStart
from huli.desktop.tray import ResidentTray, TrayUnavailableError

__all__ = [
    "AutoStartError",
    "ResidentTray",
    "TrayUnavailableError",
    "WindowsAutoStart",
]
