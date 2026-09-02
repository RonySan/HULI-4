"""Validação da fundação local de voz e das regressões de agenda."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from huli import __version__
from huli.bootstrap import build_runtime
from huli.infrastructure import Settings
from huli.voice import (
    VoiceCapabilities,
    VoiceCommand,
    VoiceService,
    VoiceSession,
    extract_wake_command,
    parse_voice_command,
)


class ValidationBackend:
    def __init__(self) -> None:
        self.spoken: list[str] = []

    def capabilities(self) -> VoiceCapabilities:
        return VoiceCapabilities(True, True, "validation-local")

    def speak(self, text: str, *, language: str, rate: int, volume: int) -> None:
        if language != "pt-BR" or not -10 <= rate <= 10 or not 0 <= volume <= 100:
            raise RuntimeError("Configuração de síntese inválida.")
        self.spoken.append(text)

    def listen_once(self, *, language: str, timeout: int) -> str:
        if language != "pt-BR" or timeout < 2:
            raise RuntimeError("Configuração de reconhecimento inválida.")
        return "o que temos na agenda"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def run_validation() -> None:
    print(f"Validando voz local e agenda natural em {__version__}...")
    backend = ValidationBackend()
    voice = VoiceService(backend)
    session = VoiceSession(voice, auto_speak=True)

    require(parse_voice_command("modo voz") is VoiceCommand.CONTINUOUS, "Comando de modo voz falhou.")
    require(
        extract_wake_command("ruli que horas são") == "que horas são",
        "Ativação local não reconheceu o nome real.",
    )
    require(
        extract_wake_command("olhe que horas são") is None,
        "Uma palavra comum foi confundida com o nome Huli.",
    )
    require(voice.listen_once() == "o que temos na agenda", "Reconhecimento controlado falhou.")
    voice.speak("Voz validada.")
    require(backend.spoken == ["Voz validada."], "Síntese controlada falhou.")
    require(not session.can_speak_response("journal.list"), "Diário privado seria lido em voz alta.")

    with TemporaryDirectory(prefix="huli-voice-") as temp_dir:
        runtime = build_runtime(
            Settings(
                environment="validation",
                log_level="CRITICAL",
                data_dir=Path(temp_dir) / "data",
            )
        )
        meta = {"session_id": "voice", "username": "rony", "role": "owner"}
        for command in ("agendas", "o que temos na agenda"):
            response = runtime.kernel.process(command, metadata=meta)
            require(response.handled_by == "agenda", f"Agenda não reconheceu: {command}")

    print("VOZ LOCAL: voz, ativacao e agenda simuladas aprovadas; hardware ainda nao testado.")


def main() -> int:
    try:
        run_validation()
        return 0
    except Exception as exc:
        print(f"VOZ LOCAL: FALHA - {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
