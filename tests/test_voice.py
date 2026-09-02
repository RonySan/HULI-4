"""Testes da fundação de voz local."""

from __future__ import annotations

import subprocess

import pytest

from huli.voice import (
    VoiceCapabilities,
    VoiceCommand,
    VoiceService,
    VoiceSession,
    VoiceTimeoutError,
    WindowsSpeechBackend,
    parse_voice_command,
)


class FakeBackend:
    def __init__(self) -> None:
        self.spoken: list[tuple[str, str, int, int]] = []

    def capabilities(self) -> VoiceCapabilities:
        return VoiceCapabilities(True, True, "fake-local")

    def speak(self, text: str, *, language: str, rate: int, volume: int) -> None:
        self.spoken.append((text, language, rate, volume))

    def listen_once(self, *, language: str, timeout: int) -> str:
        assert language == "pt-BR"
        assert timeout == 8
        return "o que temos na agenda"

    def listen_calibration_once(self, *, language: str, timeout: int, cancel_event=None) -> str:
        assert language == "pt-BR"
        assert timeout == 5
        return "ruli"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("voz", VoiceCommand.STATUS),
        ("ativar voz", VoiceCommand.ENABLE),
        ("ativar a voz", VoiceCommand.ENABLE),
        ("desligar voz", VoiceCommand.DISABLE),
        ("ouvir", VoiceCommand.LISTEN),
        ("modo voz", VoiceCommand.CONTINUOUS),
        ("escuta contínua", VoiceCommand.CONTINUOUS),
        ("parar voz", VoiceCommand.STOP),
        ("o que temos na agenda", VoiceCommand.NONE),
    ],
)
def test_voice_commands_are_deterministic(text: str, expected: VoiceCommand) -> None:
    assert parse_voice_command(text) is expected


def test_voice_service_delegates_without_network() -> None:
    backend = FakeBackend()
    service = VoiceService(backend, language="pt-BR", input_timeout=8, rate=2, volume=85)

    service.speak("Agenda vazia.")

    assert service.listen_once() == "o que temos na agenda"
    assert backend.spoken == [("Agenda vazia.", "pt-BR", 2, 85)]


def test_calibration_transcription_is_a_separate_non_command_operation() -> None:
    service = VoiceService(FakeBackend(), language="pt-BR")

    assert service.listen_calibration_once(timeout=5) == "ruli"


def test_private_journal_response_is_never_spoken_automatically() -> None:
    session = VoiceSession(VoiceService(FakeBackend()), auto_speak=True)

    assert session.can_speak_response("agenda.query")
    assert not session.can_speak_response("journal.list")


def test_windows_backend_passes_spoken_text_through_stdin() -> None:
    calls: list[dict[str, object]] = []

    def runner(*args, **kwargs):
        calls.append({"args": args, "kwargs": kwargs})
        return subprocess.CompletedProcess(args[0], 0, stdout="", stderr="")

    backend = WindowsSpeechBackend(
        executable="powershell.exe",
        platform_name="Windows",
        runner=runner,
    )
    dangerous_text = "teste $(Write-Output invasao)"

    backend.speak(dangerous_text, language="pt-BR", rate=0, volume=100)

    command = calls[0]["args"][0]
    assert dangerous_text not in command
    assert calls[0]["kwargs"]["input"] == dangerous_text


def test_windows_backend_reports_listening_timeout() -> None:
    def runner(*args, **kwargs):
        return subprocess.CompletedProcess(args[0], 3, stdout="", stderr="")

    backend = WindowsSpeechBackend(
        executable="powershell.exe",
        platform_name="Windows",
        runner=runner,
    )

    with pytest.raises(VoiceTimeoutError, match="Não ouvi"):
        backend.listen_once(language="pt-BR", timeout=2)
