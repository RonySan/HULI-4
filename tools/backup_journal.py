"""Cria um backup portátil e criptografado do diário pessoal."""

from __future__ import annotations

from getpass import getpass
from pathlib import Path

from huli.bootstrap import build_runtime
from huli.security import AuthenticationError, JournalVaultError


def main() -> int:
    runtime = build_runtime()
    username = input("Usuário proprietário: ").strip()
    password = getpass("Senha: ")
    try:
        user, token = runtime.auth.authenticate(username, password)
    except (AuthenticationError, JournalVaultError, ValueError) as exc:
        print(f"Huli: não foi possível abrir o cofre: {exc}")
        return 1

    raw_destination = input(
        "Destino do backup (Enter = pasta data/backups): "
    ).strip()
    destination = Path(raw_destination).expanduser() if raw_destination else None
    try:
        path = runtime.journal_backups.create_backup(
            owner=user.username,
            password=password,
            destination=destination,
        )
    except (JournalVaultError, OSError, ValueError) as exc:
        print(f"Huli: não foi possível criar o backup: {exc}")
        return 1
    finally:
        runtime.auth.revoke_token(token)

    print(f"Huli: backup criptografado criado em: {path}")
    print("Guarde esse arquivo fora do computador e nunca esqueça a senha.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
