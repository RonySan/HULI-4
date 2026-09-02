# ruff: noqa: E402 -- imports da Huli exigem a troca antecipada para a .venv
"""Ponto de entrada local da Huli 4 durante a staging da Fase 4."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import time


def _restart_with_project_python() -> None:
    """Usa o Python da própria Huli mesmo quando chamam ``python main.py``."""
    local_python = Path(__file__).resolve().parent / ".venv" / "Scripts" / "python.exe"
    if not local_python.is_file():
        return
    current = os.path.normcase(os.path.abspath(sys.executable))
    expected = os.path.normcase(os.path.abspath(local_python))
    if current == expected:
        return
    os.environ.setdefault("PYTHONUTF8", "1")
    try:
        completed = subprocess.run(
            [str(local_python), str(Path(__file__).resolve()), *sys.argv[1:]],
            check=False,
        )
        raise SystemExit(completed.returncode)
    except KeyboardInterrupt:
        raise SystemExit(130) from None
    except OSError as exc:
        raise SystemExit(
            "Não consegui abrir o ambiente Python da Huli. "
            "Execute .\\INICIAR_HULI.bat no PowerShell."
        ) from exc


_restart_with_project_python()

from dataclasses import dataclass, field
from getpass import getpass
from uuid import uuid4

from huli import __app_name__, __version__
from huli.bootstrap import HuliRuntime, build_runtime
from huli.brain.normalization import normalize_text
from huli.core import InvalidKernelInput
from huli.security import AuthenticationError, JournalVaultError
from huli.security.privacy import redact_private_text
from huli.voice import (
    VoiceCommand,
    VoiceError,
    VoiceService,
    VoiceSession,
    VoiceTimeoutError,
    WakeAliasStore,
    WakeWordListener,
    parse_voice_command,
    parse_wake_control,
    read_hybrid_input,
)


_WAKE_WRITE_INTENTS = frozenset(
    {
        "agenda.create",
        "agenda.cancel",
        "task.create",
        "task.complete",
        "project.set",
        "project.note",
        "memory.remember",
        "memory.forget",
    }
)


def _wake_requires_confirmation(intent: str) -> bool:
    return intent in _WAKE_WRITE_INTENTS or intent.startswith("journal.")


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
    if session.role == "owner":
        try:
            user = runtime.auth.validate_token(session.token or "")
        except AuthenticationError:
            return False
        return user.username.casefold() == session.username.casefold()
    if not session.is_guest:
        return False
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
        input_provider=settings.voice_input_provider,
        model_path=settings.voice_model_path,
        input_device=settings.voice_input_device,
    )
    return VoiceSession(service=service, auto_speak=settings.voice_auto_speak)


def _listen(voice: VoiceSession) -> str | None:
    try:
        voice.service.prepare_input()
        print("Huli: Estou ouvindo...", flush=True)
        text = voice.service.listen_once()
    except KeyboardInterrupt:
        voice.continuous = False
        print("\nHuli: Escuta encerrada. O teclado está disponível.")
        return None
    except VoiceTimeoutError as exc:
        print(f"Huli: {exc}")
        voice.continuous = False
        return None
    except VoiceError as exc:
        print(f"Huli: Voz indisponível: {exc}")
        voice.continuous = False
        return None
    print(f"Você (voz): {redact_private_text(text)}")
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
            voice.auto_speak = capabilities.output_available
            voice.continuous = True
            print("Huli: Modo de voz iniciado. Áudio local, sem gravação. Diga 'parar voz' ou pressione Ctrl+C para voltar ao teclado.")
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
    print(f"Dados locais: {runtime.settings.data_dir}")
    wake: WakeWordListener | None = None
    if runtime.settings.voice_wake_enabled:
        wake_aliases = WakeAliasStore(
            runtime.settings.data_dir / "voice_wake_aliases.json"
        ).load()
        wake = WakeWordListener(
            voice.service,
            cycle_timeout=runtime.settings.voice_wake_cycle_timeout,
            command_timeout=runtime.settings.voice_input_timeout,
            aliases=wake_aliases,
        )
        try:
            wake.start()
        except VoiceError as exc:
            wake = None
            print(f"Huli: Ativação por voz indisponível: {exc}")
        else:
            print(
                "Huli: Ativação contínua ligada. Diga 'Huli' para chamar. "
                "Ao digitar, o teclado tem prioridade."
            )
    if wake is None and runtime.settings.voice_start_listening:
        _handle_voice_command(VoiceCommand.CONTINUOUS, voice)
    pending_wake_command: tuple[str, float] | None = None
    try:
        while True:
            try:
                from_wake = False
                if voice.continuous:
                    if wake:
                        wake.pause()
                    text = _listen(voice)
                    if text is None:
                        if wake and not voice.continuous:
                            wake.resume()
                        continue
                elif wake:
                    result = read_hybrid_input(wake)
                    if result is None:
                        print("Huli: Encerrando interface local.")
                        break
                    text = result.text
                    from_wake = result.from_voice
                    if from_wake:
                        print(f"Você (voz): {redact_private_text(text)}")
                else:
                    text = input("Você: ")
            except (EOFError, KeyboardInterrupt):
                print("\nHuli: Encerrando interface local.")
                break
            try:
                if from_wake:
                    pending_wake_command = None
                if not from_wake and normalize_text(text) == "confirmar voz":
                    if pending_wake_command and time.monotonic() <= pending_wake_command[1]:
                        text = pending_wake_command[0]
                        pending_wake_command = None
                        print("Huli: Comando de voz confirmado pelo teclado.")
                    else:
                        pending_wake_command = None
                        print("Huli: Não há comando de voz aguardando confirmação.")
                        continue
                elif not from_wake:
                    pending_wake_command = None
                if text.strip().lower() in {"sair", "exit", "quit"}:
                    print("Huli: Encerrando interface local.")
                    break
                wake_control = parse_wake_control(text)
                if wake_control is not None:
                    if wake is None:
                        print("Huli: A ativação não foi iniciada nesta sessão.")
                    elif wake_control:
                        wake.enable()
                        print("Huli: Ativação por voz ligada. Diga 'Huli' para chamar.")
                    else:
                        wake.disable()
                        print("Huli: Ativação por voz pausada. O teclado continua disponível.")
                    continue
                voice_command = parse_voice_command(text)
                if voice_command is VoiceCommand.LISTEN:
                    text = _listen(voice)
                    if text is None:
                        continue
                    voice_command = parse_voice_command(text)
                    if text.strip().lower() in {"sair", "exit", "quit"}:
                        break
                if voice_command is VoiceCommand.STATUS and wake:
                    state = "ligada" if wake.enabled else "pausada"
                    print(f"Huli: {voice.status_text()} Ativação: {state}.")
                    continue
                if _handle_voice_command(voice_command, voice):
                    continue
                intent = runtime.intents.classify(text).intent.value
                if from_wake and _wake_requires_confirmation(intent):
                    pending_wake_command = (text, time.monotonic() + 30)
                    print(
                        "Huli: Esse comando altera dados. Para autorizar, digite "
                        "'confirmar voz' nos próximos 30 segundos."
                    )
                    continue
                if not _can_execute(runtime, session, text):
                    if not session.is_guest:
                        voice.continuous = False
                        runtime.context.clear(session.session_id)
                        print("Huli: Sua sessão expirou ou foi revogada. Autentique novamente.")
                        session = _authenticate(runtime)
                    else:
                        print("Huli: Essa ação exige acesso do proprietário. Você está como visitante.")
                    continue
                try:
                    runtime.security.validate_input(text)
                    response = runtime.kernel.process(text, metadata=_metadata(session))
                except (InvalidKernelInput, ValueError) as exc:
                    print(f"Huli: {exc}")
                    continue
                print(f"Huli: {response.text}")
                if voice.can_speak_response(intent) and response.handled_by != "journal":
                    try:
                        voice.service.speak(response.text)
                    except VoiceError as exc:
                        voice.auto_speak = False
                        voice.continuous = False
                        print(f"Huli: A fala foi desativada após uma falha: {exc}")
            finally:
                if wake and not voice.continuous:
                    wake.resume()
    finally:
        if wake:
            wake.stop()
        runtime.context.clear(session.session_id)
        if session.token:
            runtime.auth.revoke_token(session.token)


def main() -> None:
    run_cli()


if __name__ == "__main__":
    main()
