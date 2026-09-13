"""Conecta e sincroniza a agenda principal do Google Calendar."""

from __future__ import annotations

import argparse

from huli.bootstrap import build_runtime
from huli.integrations import GoogleCalendarError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Integração local da Huli com Google Calendar.")
    parser.add_argument("action", choices=("status", "connect", "connect-write", "sync", "disconnect"))
    args = parser.parse_args(argv)
    runtime = build_runtime()
    calendar = runtime.google_calendar
    try:
        if args.action == "status":
            print(f"Huli: {calendar.status_text()}")
            print(f"Credencial OAuth: {calendar.credentials_path}")
            return 0
        if args.action == "connect":
            result = calendar.connect()
            print(f"Huli: Google Calendar conectado. {result.summary()}")
            return 0
        if args.action == "connect-write":
            result = calendar.connect(write_access=True)
            print(f"Huli: Google Calendar autorizado para criar eventos após confirmação. {result.summary()}")
            return 0
        if args.action == "sync":
            result = calendar.sync()
            print(f"Huli: Google Calendar sincronizado. {result.summary()}")
            return 0
        calendar.disconnect()
        print("Huli: Google Calendar desconectado desta conta do Windows.")
        return 0
    except GoogleCalendarError as exc:
        print(f"Huli: Google Calendar indisponível: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
