"""Ponto de entrada local da Huli 4 durante a Fase 0."""

from __future__ import annotations

from getpass import getpass

from huli import __app_name__, __version__
from huli.bootstrap import HuliRuntime, build_runtime
from huli.core import InvalidKernelInput
from huli.security import AuthenticationError


def _first_run_setup(runtime: HuliRuntime) -> None:
    print("Primeira inicialização: configure a identidade proprietária da Huli.")
    while True:
        username = input("Usuário: ").strip()
        password = getpass("Nova senha: ")
        confirmation = getpass("Confirme a senha: ")
        if password != confirmation:
            print("Huli: As senhas não coincidem.")
            continue
        try:
            runtime.auth.create_owner(username, password)
        except ValueError as exc:
            print(f"Huli: {exc}")
            continue
        print("Huli: Identidade proprietária configurada com sucesso.")
        return


def _authenticate(runtime: HuliRuntime) -> tuple[str, str]:
    if not runtime.auth.has_users():
        _first_run_setup(runtime)

    for _attempt in range(3):
        username = input("Usuário: ").strip()
        password = getpass("Senha: ")
        try:
            user, token = runtime.auth.authenticate(username, password)
        except (AuthenticationError, ValueError):
            print("Huli: Usuário ou senha inválidos.")
            continue
        return user.username, token

    raise AuthenticationError("Número máximo de tentativas de autenticação excedido.")


def run_cli() -> None:
    """Executa a interface local usada para validar a fundação."""
    runtime = build_runtime()

    print(f"{__app_name__} {__version__} — Fase 0 em construção.")
    try:
        username, token = _authenticate(runtime)
    except AuthenticationError as exc:
        print(f"Huli: {exc}")
        return

    print(f"Huli: Bem-vindo, {username}.")
    print("Kernel + Skill Registry ativos. Digite 'sair' para encerrar.")

    try:
        while True:
            try:
                text = input("Você: ")
            except (EOFError, KeyboardInterrupt):
                print("\nHuli: Encerrando interface local.")
                break

            if text.strip().lower() in {"sair", "exit", "quit"}:
                print("Huli: Encerrando interface local.")
                break

            try:
                runtime.security.validate_input(text)
                response = runtime.kernel.process(text)
            except (InvalidKernelInput, ValueError) as exc:
                print(f"Huli: {exc}")
                continue

            print(f"Huli: {response.text}")
    finally:
        runtime.auth.revoke_token(token)


def main() -> None:
    """Inicializa a interface local da Huli."""
    run_cli()


if __name__ == "__main__":
    main()
