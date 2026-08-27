"""Cria ou troca a senha local do proprietário da Huli."""

from __future__ import annotations

from getpass import getpass

from huli.bootstrap import build_runtime
from huli.security import AuthenticationError


def main() -> int:
    runtime = build_runtime()
    username = input("Usuário proprietário: ").strip()
    current_password = getpass("Senha atual (Enter se ainda não houver senha): ")

    try:
        user, token = runtime.auth.authenticate(username, current_password)
    except (AuthenticationError, ValueError):
        print("Huli: usuário ou senha atual inválidos.")
        return 1

    new_password = getpass("Nova senha: ").strip()
    confirmation = getpass("Confirme a nova senha: ").strip()
    if new_password != confirmation:
        runtime.auth.revoke_token(token)
        print("Huli: as novas senhas não coincidem.")
        return 1
    if not new_password:
        runtime.auth.revoke_token(token)
        print("Huli: o diário exige uma senha não vazia.")
        return 1

    try:
        runtime.auth.set_password(user.username, new_password)
    except (AuthenticationError, ValueError) as exc:
        runtime.auth.revoke_token(token)
        print(f"Huli: não foi possível alterar a senha: {exc}")
        return 1

    runtime.auth.revoke_token(token)
    print(f"Huli: senha de '{user.username}' atualizada com sucesso.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
