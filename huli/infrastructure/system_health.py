"""Leitura local e somente leitura da saude do computador."""

from __future__ import annotations

from dataclasses import dataclass
import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import shutil
import time
from typing import Callable


@dataclass(frozen=True, slots=True)
class SystemHealthSnapshot:
    cpu_percent: float | None
    memory_percent: float | None
    disk_percent: float
    disk_name: str
    battery_percent: int | None
    battery_plugged: bool | None
    uptime_seconds: float | None


class _FileTime(ctypes.Structure):
    _fields_ = (("low", wintypes.DWORD), ("high", wintypes.DWORD))

    @property
    def value(self) -> int:
        return (int(self.high) << 32) | int(self.low)


class _MemoryStatus(ctypes.Structure):
    _fields_ = (
        ("length", wintypes.DWORD),
        ("memory_load", wintypes.DWORD),
        ("total_physical", ctypes.c_ulonglong),
        ("available_physical", ctypes.c_ulonglong),
        ("total_page_file", ctypes.c_ulonglong),
        ("available_page_file", ctypes.c_ulonglong),
        ("total_virtual", ctypes.c_ulonglong),
        ("available_virtual", ctypes.c_ulonglong),
        ("available_extended_virtual", ctypes.c_ulonglong),
    )


class _PowerStatus(ctypes.Structure):
    _fields_ = (
        ("ac_line_status", ctypes.c_ubyte),
        ("battery_flag", ctypes.c_ubyte),
        ("battery_life_percent", ctypes.c_ubyte),
        ("system_status_flag", ctypes.c_ubyte),
        ("battery_life_time", wintypes.DWORD),
        ("battery_full_life_time", wintypes.DWORD),
    )


class SystemHealthMonitor:
    """Coleta indicadores sem executar programas nem transmitir dados."""

    def __init__(
        self,
        disk_path: Path | str,
        *,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        path = Path(disk_path).resolve()
        self.disk_path = Path(path.anchor or path)
        self._sleep = sleeper

    def snapshot(self) -> SystemHealthSnapshot:
        disk = shutil.disk_usage(self.disk_path)
        disk_percent = (disk.used / disk.total * 100) if disk.total else 0.0
        cpu = memory = uptime = None
        battery = None
        plugged = None
        if os.name == "nt":
            cpu = self._windows_cpu_percent()
            memory = self._windows_memory_percent()
            uptime = self._windows_uptime()
            battery, plugged = self._windows_battery()
        return SystemHealthSnapshot(
            cpu_percent=cpu,
            memory_percent=memory,
            disk_percent=disk_percent,
            disk_name=self.disk_path.anchor.rstrip("\\/") or str(self.disk_path),
            battery_percent=battery,
            battery_plugged=plugged,
            uptime_seconds=uptime,
        )

    def _windows_cpu_percent(self) -> float | None:
        kernel32 = ctypes.windll.kernel32

        def sample() -> tuple[int, int, int] | None:
            idle = _FileTime()
            kernel = _FileTime()
            user = _FileTime()
            if not kernel32.GetSystemTimes(
                ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)
            ):
                return None
            return idle.value, kernel.value, user.value

        first = sample()
        if first is None:
            return None
        self._sleep(0.12)
        second = sample()
        if second is None:
            return None
        idle_delta = second[0] - first[0]
        total_delta = (second[1] - first[1]) + (second[2] - first[2])
        if total_delta <= 0:
            return None
        return max(0.0, min(100.0, (total_delta - idle_delta) / total_delta * 100))

    @staticmethod
    def _windows_memory_percent() -> float | None:
        status = _MemoryStatus()
        status.length = ctypes.sizeof(_MemoryStatus)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return None
        return float(status.memory_load)

    @staticmethod
    def _windows_uptime() -> float | None:
        try:
            return float(ctypes.windll.kernel32.GetTickCount64()) / 1000
        except (AttributeError, OSError):
            return None

    @staticmethod
    def _windows_battery() -> tuple[int | None, bool | None]:
        status = _PowerStatus()
        if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status)):
            return None, None
        no_battery = status.battery_flag in {128, 255}
        percent = None if no_battery or status.battery_life_percent == 255 else int(status.battery_life_percent)
        plugged = None if status.ac_line_status == 255 else status.ac_line_status == 1
        return percent, plugged
