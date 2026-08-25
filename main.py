"""Ponto de entrada local da Huli 4 durante a Fase 0."""

from __future__ import annotations

from dataclasses import dataclass
from getpass import getpass

from huli import __app_name__, __version__
from huli.bootstrap import HuliRuntime, build_runtime
from huli.core import InvalidKernelInput
from huli.security import AuthenticationError


@dataclass(frozen=True, slots=True)
class CliSession:
    username: str
    role: str
    token: str | None = None

    @property
    def is_guest(self) -> bool:
        return self.role == "guest"


def _first_run_setup(runtime: HuliRuntime) -> CliSession:
    print("Primeira inicialização: configure o proprietário ou entre como visitante.")
    username = input("Usuário proprietário (Enter = visitante): ").strip()
    if not username:
        print("Huli: Continuando como visitante. O proprietário pode ser configurado depois.")
        return CliSession(username="Visitante", role="guest")

    while True:
        password = getpass("Nova senha (opcional, Enter = sem senha): ")
        if password:
            confirmation = getpass("Confirme a senha: ")
            if password != confirmation:
                print("Huli: As senhas não coincidem.")
                continue
        try:
            runtime.auth.create_owner(username, password)
            user, token = runtime.auth.authenticate(username, password)
        except ValueError as exc:
            print(f"Huli: {exc}")
            username = input("Usuário proprietário (Enter = visitante): ").strip()
            if not username:
                print("Huli: Continuando como visitante.")
                return CliSession(username="Visitante", role="guest")
            continue
        print("Huli: Identidade proprietária configurada com sucesso.")
        if not password:
            print("Huli: Proprietário configurado sem senha local.")
        return CliSession(username=user.username, role="owner", token=token)


def _authenticate(runtime: HuliRuntime) -> CliSession:
    if not runtime.auth.has_users():
        return _first_run_setup(runtime)

    for _attempt in range(3):
        username = input("Usuário (Enter = visitante): ").strip()
        if not username:
            return CliSession(username="Visitante", role="guest")

        known_user = runtime.auth.find_user(username)
        if known_user is None:
            print(f"Huli: Usuário '{username}' não reconhecido. Acesso como visitante.")
            return CliSession(username=username, role="guest")

        password = ""
        if runtime.auth.requires_password(known_user.username):
            password = getpass("Senha: ")

        try:
            user, token = runtime.auth.authenticate(known_user.username, password)
        except (AuthenticationError, ValueError):
            print("Huli: Senha inválida.")
            continue
        return CliSession(username=user.username, role="owner", token=token)

    print("Huli: Limite de tentativas atingido. Entrando como visitante.")
    return CliSession(username="Visitante", role="guest")


def _can_execute(runtime: HuliRuntime, session: CliSession, text: str) -> bool:
    if not session.is_guest:
        return True
    return runtime.security.guest_can_execute(text)


def run_cli() -> None:
    """Executa a interface local usada para validar a fundação."""
    runtime = build_runtime()

    print(f"{__app_name__} {__version__} — Fase 0 em construção.")
    session = _authenticate(runtime)

    if session.is_guest:
        print(f"Huli: Bem-vindo, {session.username}. Modo visitante com acesso limitado.")
        print("Visitante pode usar: ping, status, status huli e teste.")
    else:
        print(f"Huli: Bem-vindo, {session.username}.")

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

            if not _can_execute(runtime, session, text):
                print("Huli: Essa ação exige acesso do proprietário. Você está como visitante.")
                continue

            try:
                runtime.security.validate_input(text)
                response = runtime.kernel.process(text)
            except (InvalidKernelInput, ValueError) as exc:
                print(f"Huli: {exc}")
                continue

            print(f"Huli: {response.text}")
    finally:
        if session.token:
            runtime.auth.revoke_token(session.token)


def main() -> None:
    """Inicializa a interface local da Huli."""
    run_cli()


if __name__ == "__main__":
    main()
