"""Inicializador do painel que sempre usa o ambiente Python da Huli."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

from huli.desktop.startup_report import StartupReporter


APP_ROOT = Path(__file__).resolve().parent

def apply_launch_options(argv: list[str]) -> None:
    """Traduz opções do atalho em configuração antes de construir o runtime."""
    if "--resident" in argv:
        os.environ["HULI_DESKTOP_RESIDENT_ENABLED"] = "true"
        os.environ["HULI_VOICE_WAKE_ENABLED"] = "true"
        os.environ["HULI_VOICE_AUTO_SPEAK"] = "true"
    if "--minimized" in argv:
        os.environ["HULI_DESKTOP_START_MINIMIZED"] = "true"


apply_launch_options(sys.argv[1:])


def _restart_with_project_python() -> None:
    local_python = Path(__file__).resolve().parent / ".venv" / "Scripts" / "python.exe"
    if not local_python.is_file():
        return
    current = os.path.normcase(os.path.abspath(sys.executable))
    expected = os.path.normcase(os.path.abspath(local_python))
    if current == expected:
        return
    completed = subprocess.run(
        [str(local_python), str(Path(__file__).resolve()), *sys.argv[1:]],
        check=False,
    )
    raise SystemExit(completed.returncode)


def run() -> None:
    _restart_with_project_python()
    reporter = StartupReporter(APP_ROOT / "data") if "--startup" in sys.argv[1:] else None
    if reporter:
        reporter.starting()
    try:
        from huli_preflight import ensure_core  # noqa: PLC0415

        ensure_core()

        from huli.gui import main  # noqa: PLC0415

        if reporter:
            reporter.ready()
        main()
    except BaseException as exc:
        if reporter:
            reporter.failed(exc)
        raise


if __name__ == "__main__":
    run()
