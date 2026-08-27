"""Ponto de entrada local da Huli 4 durante a staging da Fase 4."""

from __future__ import annotations

from dataclasses import dataclass, field
from getpass import getpass
from uuid import uuid4

from huli import __app_name__, __version__
from huli.bootstrap import HuliRuntime, build_runtime
from huli.core import InvalidKernelInput
from huli.security import AuthenticationError


@dataclass(frozen=True, slots=True)
class CliSession:
    username: str
    role: str
    token: str | None = None
    session_id: str = field(default_factory=lambda: f"cli-{uuid4().hex}")

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
        password = getpass(
            "Nova senha (opcional; o diário privado exige senha): "
        ).strip()
        if password:
            confirmation = getpass("Confirme a senha: ").strip()
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
                return CliSession(username="Visitante", role="guest")
            continue
        print("Huli: Identidade proprietária configurada com sucesso.")
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
            password = getpass("Senha: ").strip()
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
    intent = runtime.intents.classify(text).intent.value
    return runtime.security.guest_can_execute(text, intent)


def _metadata(session: CliSession) -> dict[str, object]:
    return {
        "session_id": session.session_id,
        "username": session.username,
        "role": session.role,
    }


def run_cli() -> None:
    runtime = build_runtime()
    print(f"{__app_name__} {__version__} — Fase 4.1 staging: diário pessoal privado.")
    session = _authenticate(runtime)
    if session.is_guest:
        print(f"Huli: Bem-vindo, {session.username}. Modo visitante com acesso limitado.")
        print("Visitante pode usar conversa básica, horário, ping e status.")
    else:
        print(f"Huli: Bem-vindo, {session.username}.")
    print(
        "Recursos atuais: contexto, tarefas, agenda, resumo, projetos, memória, "
        "conhecimento estruturado, personalidade contextual e diário privado."
    )
    if not session.is_guest and runtime.auth.requires_password(session.username):
        print(
            "Diário: use 'diário: seu texto' ou 'como uso meu diário?' para ver os exemplos."
        )
    elif not session.is_guest:
        print(
            "Diário bloqueado: configure uma senha com "
            "'python tools/set_local_password.py'."
        )
    print("Digite 'sair' para encerrar.")
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
                response = runtime.kernel.process(text, metadata=_metadata(session))
            except (InvalidKernelInput, ValueError) as exc:
                print(f"Huli: {exc}")
                continue
            print(f"Huli: {response.text}")
    finally:
        runtime.context.clear(session.session_id)
        if session.token:
            runtime.auth.revoke_token(session.token)


def main() -> None:
    run_cli()


if __name__ == "__main__":
    main()
