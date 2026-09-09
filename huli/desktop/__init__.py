"""Integrações locais do modo residente da Huli."""

from huli.desktop.autostart import AutoStartError, WindowsAutoStart
from huli.desktop.startup_report import StartupReporter, StartupState
from huli.desktop.tray import ResidentTray, TrayUnavailableError

__all__ = [
    "AutoStartError",
    "ResidentTray",
    "StartupReporter",
    "StartupState",
    "TrayUnavailableError",
    "WindowsAutoStart",
]
