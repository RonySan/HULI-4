"""Restaura um backup criptografado com confirmação destrutiva explícita."""

from __future__ import annotations

from getpass import getpass
from pathlib import Path

from huli.bootstrap import build_runtime
from huli.security import (
    AuthenticationError,
    EncryptedFileError,
    JournalVaultError,
)


def main() -> int:
    runtime = build_runtime()
    source = Path(input("Arquivo .hulibak: ").strip()).expanduser()
    username = input("Usuário proprietário: ").strip()
    password = getpass("Senha atual do proprietário: ")
    try:
        user, token = runtime.auth.authenticate(username, password)
    except (AuthenticationError, JournalVaultError, ValueError) as exc:
        print(f"Huli: não foi possível abrir o cofre: {exc}")
        return 1

    backup_password = getpass(
        "Senha usada quando o backup foi criado (Enter = senha atual): "
    )
    if not backup_password:
        backup_password = password

    existing = runtime.journal_repository.count_all(user.username)
    replace = False
    if existing:
        print(
            f"Atenção: o diário atual possui {existing} entrada(s). "
            "Uma cópia de segurança será criada antes da substituição."
        )
        replace = input("Digite RESTAURAR para confirmar: ").strip() == "RESTAURAR"
        if not replace:
            runtime.auth.revoke_token(token)
            print("Huli: restauração cancelada; nenhum dado foi alterado.")
            return 1

    try:
        result = runtime.journal_backups.restore_backup(
            owner=user.username,
            password=backup_password,
            source=source,
            replace_existing=replace,
        )
    except (EncryptedFileError, JournalVaultError, OSError, ValueError) as exc:
        print(f"Huli: restauração recusada: {exc}")
        return 1
    finally:
        runtime.auth.revoke_token(token)

    print(f"Huli: {result.restored_entries} entrada(s) restaurada(s) com sucesso.")
    if result.safety_backup:
        print(f"Backup do diário anterior: {result.safety_backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
