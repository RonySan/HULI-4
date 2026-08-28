"""Ponto de entrada local da Huli 4 durante a staging da Fase 4."""

from __future__ import annotations

from dataclasses import dataclass, field
from getpass import getpass
from uuid import uuid4

from huli import __app_name__, __version__
from huli.bootstrap import HuliRuntime, build_runtime
from huli.core import InvalidKernelInput
from huli.security import AuthenticationError, JournalVaultError
from huli.voice import (
    VoiceCommand,
    VoiceError,
    VoiceService,
    VoiceSession,
    VoiceTimeoutError,
    parse_voice_command,
)


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
        except (ValueError, JournalVaultError) as exc:
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
        except JournalVaultError as exc:
            print(f"Huli: credenciais válidas, mas o cofre não pôde ser aberto: {exc}")
            continue
        except (AuthenticationError, ValueError):
            print("Huli: Senha inválida.")
            continue
        if password and len(password) < runtime.security.min_password_length:
            print(
                "Huli: sua senha antiga ainda funciona, mas é curta para proteger o "
                "cofre. Atualize com: python tools/set_local_password.py"
            )
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


def _build_voice_session(runtime: HuliRuntime) -> VoiceSession:
    settings = runtime.settings
    service = VoiceService.local_default(
        language=settings.voice_language,
        input_timeout=settings.voice_input_timeout,
        rate=settings.voice_rate,
        volume=settings.voice_volume,
    )
    return VoiceSession(service=service, auto_speak=settings.voice_auto_speak)


def _listen(voice: VoiceSession) -> str | None:
    print("Huli: Estou ouvindo...")
    try:
        text = voice.service.listen_once()
    except VoiceTimeoutError as exc:
        print(f"Huli: {exc}")
        voice.continuous = False
        return None
    except VoiceError as exc:
        print(f"Huli: Voz indisponível: {exc}")
        voice.continuous = False
        return None
    print(f"Você (voz): {text}")
    return text


def _handle_voice_command(command: VoiceCommand, voice: VoiceSession) -> bool:
    if command is VoiceCommand.NONE:
        return False
    if command is VoiceCommand.STATUS:
        print(f"Huli: {voice.status_text()}")
    elif command is VoiceCommand.ENABLE:
        if not voice.service.capabilities().output_available:
            print(f"Huli: {voice.status_text()}")
        else:
            voice.auto_speak = True
            print("Huli: Respostas por voz ativadas.")
            try:
                voice.service.speak("Respostas por voz ativadas.")
            except VoiceError as exc:
                voice.auto_speak = False
                print(f"Huli: Não consegui ativar a fala: {exc}")
    elif command is VoiceCommand.DISABLE:
        voice.auto_speak = False
        voice.continuous = False
        print("Huli: Respostas por voz desativadas.")
    elif command is VoiceCommand.CONTINUOUS:
        capabilities = voice.service.capabilities()
        if not capabilities.input_available:
            print(f"Huli: Voz indisponível. {capabilities.detail}")
        else:
            voice.auto_speak = True
            voice.continuous = True
            print("Huli: Modo de voz iniciado. Diga 'parar voz' para voltar ao teclado.")
    elif command is VoiceCommand.STOP:
        voice.continuous = False
        print("Huli: Modo contínuo encerrado. O teclado continua disponível.")
    return True


def run_cli() -> None:
    runtime = build_runtime()
    voice = _build_voice_session(runtime)
    print(f"{__app_name__} {__version__} — Voz local para Windows.")
    session = _authenticate(runtime)
    if session.is_guest:
        print(f"Huli: Bem-vindo, {session.username}. Modo visitante com acesso limitado.")
        print("Visitante pode usar conversa básica, horário, ping e status.")
    else:
        print(f"Huli: Bem-vindo, {session.username}.")
        unlock_result = runtime.journal_vault.last_unlock_result(session.username)
        if unlock_result and unlock_result.migrated_entries:
            print(
                f"Huli: {unlock_result.migrated_entries} entrada(s) antiga(s) foram "
                "criptografadas com segurança."
            )
            print(f"Backup de migração: {unlock_result.migration_backup}")
    print(
        "Recursos atuais: contexto, tarefas, agenda, resumo, projetos, memória, "
        "conhecimento estruturado, personalidade contextual, diário privado e voz."
    )
    if not session.is_guest and runtime.auth.requires_password(session.username):
        print(
            "Cofre aberto: use 'diário: seu texto' ou 'como uso meu diário?' para os exemplos."
        )
    elif not session.is_guest:
        print(
            "Diário bloqueado: configure uma senha com "
            "'python tools/set_local_password.py'."
        )
    print(
        "Voz: use 'voz', 'ativar voz', 'ouvir' ou 'modo voz'. "
        "Digite 'sair' para encerrar."
    )
    try:
        while True:
            if voice.continuous:
                text = _listen(voice)
                if text is None:
                    continue
            else:
                try:
                    text = input("Você: ")
                except (EOFError, KeyboardInterrupt):
                    print("\nHuli: Encerrando interface local.")
                    break
            if text.strip().lower() in {"sair", "exit", "quit"}:
                print("Huli: Encerrando interface local.")
                break
            voice_command = parse_voice_command(text)
            if voice_command is VoiceCommand.LISTEN:
                text = _listen(voice)
                if text is None:
                    continue
                voice_command = parse_voice_command(text)
            if _handle_voice_command(voice_command, voice):
                continue
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
            intent = runtime.intents.classify(text).intent.value
            if voice.can_speak_response(intent):
                try:
                    voice.service.speak(response.text)
                except VoiceError as exc:
                    voice.auto_speak = False
                    voice.continuous = False
                    print(f"Huli: A fala foi desativada após uma falha: {exc}")
    finally:
        runtime.context.clear(session.session_id)
        if session.token:
            runtime.auth.revoke_token(session.token)


def main() -> None:
    run_cli()


if __name__ == "__main__":
    main()
