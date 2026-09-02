"""Inicializador do painel que sempre usa o ambiente Python da Huli."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


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


_restart_with_project_python()

from huli.gui import main  # noqa: E402


if __name__ == "__main__":
    main()
