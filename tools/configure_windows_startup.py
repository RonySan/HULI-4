"""Ativa, remove ou consulta o início automático da Huli no Windows."""

from __future__ import annotations

import argparse

from huli.desktop import AutoStartError, WindowsAutoStart
from huli.infrastructure.config import APP_ROOT


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Configura a Huli no início do Windows.")
    parser.add_argument("action", choices=("enable", "disable", "status"))
    args = parser.parse_args(argv)
    autostart = WindowsAutoStart(APP_ROOT)
    try:
        if args.action == "enable":
            autostart.enable()
            print("Huli: início automático ativado.")
        elif args.action == "disable":
            autostart.disable()
            print("Huli: início automático desativado.")
        else:
            state = "ativado" if autostart.is_enabled() else "desativado"
            print(f"Huli: início automático {state}.")
    except AutoStartError as exc:
        print(f"Huli: não foi possível alterar o início automático: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
