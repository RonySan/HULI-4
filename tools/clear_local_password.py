"""Utilitário local para remover a senha do proprietário da Huli."""

from __future__ import annotations

from getpass import getpass

from huli.bootstrap import build_runtime
from huli.security import AuthenticationError


def main() -> int:
    runtime = build_runtime()
    username = input("Usuário proprietário: ").strip()
    current_password = getpass("Senha atual: ")

    try:
        user, token = runtime.auth.authenticate(username, current_password)
        runtime.auth.revoke_token(token)
        runtime.auth.set_password(user.username, "")
    except (AuthenticationError, ValueError) as exc:
        print(f"Huli: não foi possível remover a senha: {exc}")
        return 1

    print(f"Huli: senha local removida de '{user.username}'.")
    print("Na próxima inicialização, basta informar o nome do proprietário.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
