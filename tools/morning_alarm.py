"""Despertador visual e sonoro da rotina matinal da Huli."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk
import winsound


APP_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = APP_ROOT / "data" / "morning_alarm.json"
DEFAULT_SNOOZE_MINUTES = 10
DEFAULT_NOTES = (
    (392, 280),
    (523, 280),
    (659, 350),
    (523, 280),
    (440, 280),
    (587, 280),
    (698, 450),
)


def load_config(path: Path = CONFIG_PATH) -> dict[str, object]:
    defaults: dict[str, object] = {
        "time": "05:50",
        "audio_path": "",
        "snooze_minutes": DEFAULT_SNOOZE_MINUTES,
    }
    try:
        loaded = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return defaults
    if isinstance(loaded, dict):
        defaults.update(loaded)
    return defaults


def find_pythonw() -> Path:
    current = Path(sys.executable)
    candidate = current.with_name("pythonw.exe")
    return candidate if candidate.exists() else current


def morning_panel_environment() -> dict[str, str]:
    environment = os.environ.copy()
    environment["HULI_VOICE_WAKE_ENABLED"] = "true"
    environment["HULI_VOICE_AUTO_SPEAK"] = "true"
    return environment


class MorningAlarm:
    def __init__(self, config: dict[str, object] | None = None) -> None:
        self.config = config or load_config()
        self.stop_event = threading.Event()
        self.audio_thread: threading.Thread | None = None
        self.root = tk.Tk()
        self.root.title("Huli — Despertador matinal")
        self.root.geometry("560x330")
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)
        self.root.protocol("WM_DELETE_WINDOW", self.stop)
        self.status = tk.StringVar(value="Bom dia, Rony. Está na hora de levantar.")
        self._build()

    def _build(self) -> None:
        frame = ttk.Frame(self.root, padding=28)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Bom dia!", font=("Segoe UI", 28, "bold")).pack(pady=(8, 12))
        ttk.Label(
            frame,
            textvariable=self.status,
            font=("Segoe UI", 13),
            wraplength=490,
            justify="center",
        ).pack(pady=(0, 28))
        ttk.Button(
            frame,
            text="Estou acordado — abrir a Huli",
            command=self.open_huli,
        ).pack(fill="x", ipady=7, pady=5)
        ttk.Button(
            frame,
            text=f"Soneca por {self.snooze_minutes} minutos",
            command=self.snooze,
        ).pack(fill="x", ipady=5, pady=5)
        ttk.Button(frame, text="Parar despertador", command=self.stop).pack(
            fill="x", ipady=4, pady=5
        )

    @property
    def snooze_minutes(self) -> int:
        try:
            return max(1, min(int(self.config.get("snooze_minutes", 10)), 60))
        except (TypeError, ValueError):
            return DEFAULT_SNOOZE_MINUTES

    @property
    def audio_path(self) -> Path | None:
        raw = str(self.config.get("audio_path", "") or "").strip()
        if not raw:
            return None
        path = Path(raw).expanduser()
        return path if path.is_file() and path.suffix.casefold() == ".wav" else None

    def start_sound(self) -> None:
        self.stop_sound()
        self.stop_event.clear()
        if self.audio_path:
            winsound.PlaySound(
                str(self.audio_path),
                winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_LOOP,
            )
            return
        self.audio_thread = threading.Thread(target=self._play_melody, daemon=True)
        self.audio_thread.start()

    def _play_melody(self) -> None:
        while not self.stop_event.is_set():
            for frequency, duration in DEFAULT_NOTES:
                if self.stop_event.is_set():
                    return
                try:
                    winsound.Beep(frequency, duration)
                except RuntimeError:
                    winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
                if self.stop_event.wait(0.08):
                    return
            if self.stop_event.wait(0.8):
                return

    def stop_sound(self) -> None:
        self.stop_event.set()
        winsound.PlaySound(None, 0)

    def snooze(self) -> None:
        self.stop_sound()
        self.status.set(f"Certo. Volto em {self.snooze_minutes} minutos.")
        self.root.withdraw()
        self.root.after(self.snooze_minutes * 60 * 1000, self._resume)

    def _resume(self) -> None:
        self.status.set("Bom dia, Rony. A soneca terminou.")
        self.root.deiconify()
        self.root.lift()
        self.start_sound()

    def open_huli(self) -> None:
        self.stop_sound()
        subprocess.Popen(
            [str(find_pythonw()), str(APP_ROOT / "painel.py")],
            cwd=APP_ROOT,
            env=morning_panel_environment(),
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        self.root.destroy()

    def stop(self) -> None:
        self.stop_sound()
        self.root.destroy()

    def run(self) -> None:
        self.start_sound()
        self.root.mainloop()


def main() -> int:
    MorningAlarm().run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
