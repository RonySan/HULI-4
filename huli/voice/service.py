"""Entrada e saída de voz local da Huli no Windows."""

from __future__ import annotations

from dataclasses import dataclass
import platform
import shutil
import subprocess
from typing import Callable, Protocol


class VoiceError(RuntimeError):
    """Falha controlada da interface de voz."""


class VoiceUnavailableError(VoiceError):
    """O sistema não oferece o recurso de voz solicitado."""


class VoiceTimeoutError(VoiceError):
    """Nenhuma fala foi reconhecida no tempo configurado."""


@dataclass(frozen=True, slots=True)
class VoiceCapabilities:
    output_available: bool
    input_available: bool
    provider: str
    detail: str = ""


class VoiceBackend(Protocol):
    def capabilities(self) -> VoiceCapabilities: ...

    def speak(self, text: str, *, language: str, rate: int, volume: int) -> None: ...

    def listen_once(self, *, language: str, timeout: int) -> str: ...


Runner = Callable[..., subprocess.CompletedProcess[str]]


class WindowsSpeechBackend:
    """Usa System.Speech localmente; o texto nunca é interpolado no script."""

    _SPEAK_SCRIPT = r"""
Add-Type -AssemblyName System.Speech
$text = [Console]::In.ReadToEnd()
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$voice = $synth.GetInstalledVoices() |
    Where-Object { $_.Enabled -and $_.VoiceInfo.Culture.Name -eq $env:HULI_SPEECH_LANGUAGE } |
    Select-Object -First 1
if ($null -ne $voice) { $synth.SelectVoice($voice.VoiceInfo.Name) }
$synth.Rate = [int]$env:HULI_SPEECH_RATE
$synth.Volume = [int]$env:HULI_SPEECH_VOLUME
$synth.Speak($text)
""".strip()

    _LISTEN_SCRIPT = r"""
Add-Type -AssemblyName System.Speech
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$installed = [System.Speech.Recognition.SpeechRecognitionEngine]::InstalledRecognizers()
$recognizer = $installed |
    Where-Object { $_.Culture.Name -eq $env:HULI_SPEECH_LANGUAGE } |
    Select-Object -First 1
if ($null -eq $recognizer) {
    $prefix = $env:HULI_SPEECH_LANGUAGE.Split('-')[0]
    $recognizer = $installed |
        Where-Object { $_.Culture.TwoLetterISOLanguageName -eq $prefix } |
        Select-Object -First 1
}
if ($null -eq $recognizer) {
    [Console]::Error.Write('Instale o pacote de fala em português do Windows.')
    exit 4
}
$engine = New-Object System.Speech.Recognition.SpeechRecognitionEngine($recognizer)
$engine.LoadGrammar((New-Object System.Speech.Recognition.DictationGrammar))
try {
    $engine.SetInputToDefaultAudioDevice()
    $result = $engine.Recognize([TimeSpan]::FromSeconds([int]$env:HULI_SPEECH_TIMEOUT))
} finally {
    $engine.Dispose()
}
if ($null -eq $result -or [string]::IsNullOrWhiteSpace($result.Text)) { exit 3 }
[Console]::Write($result.Text)
""".strip()

    def __init__(
        self,
        *,
        executable: str | None = None,
        platform_name: str | None = None,
        runner: Runner = subprocess.run,
    ) -> None:
        self.platform_name = platform_name or platform.system()
        self.executable = executable or shutil.which("powershell") or shutil.which("pwsh")
        self._runner = runner

    def capabilities(self) -> VoiceCapabilities:
        available = self.platform_name == "Windows" and bool(self.executable)
        detail = (
            "Microsoft System.Speech local"
            if available
            else "A voz local desta versão requer Windows e PowerShell."
        )
        return VoiceCapabilities(available, available, "windows-system-speech", detail)

    def speak(self, text: str, *, language: str, rate: int, volume: int) -> None:
        self._ensure_available()
        clean_text = " ".join(str(text or "").split())
        if not clean_text:
            return
        result = self._run(
            self._SPEAK_SCRIPT,
            input_text=clean_text,
            environment={
                "HULI_SPEECH_LANGUAGE": language,
                "HULI_SPEECH_RATE": str(rate),
                "HULI_SPEECH_VOLUME": str(volume),
            },
            timeout=max(15, min(120, len(clean_text) // 8 + 15)),
        )
        if result.returncode != 0:
            raise VoiceError(self._failure_message(result, "Não consegui reproduzir a voz."))

    def listen_once(self, *, language: str, timeout: int) -> str:
        self._ensure_available()
        result = self._run(
            self._LISTEN_SCRIPT,
            environment={
                "HULI_SPEECH_LANGUAGE": language,
                "HULI_SPEECH_TIMEOUT": str(timeout),
            },
            timeout=timeout + 15,
        )
        if result.returncode == 3:
            raise VoiceTimeoutError("Não ouvi nenhum comando. Voltando ao teclado.")
        if result.returncode == 4:
            raise VoiceUnavailableError(
                self._failure_message(
                    result,
                    "Instale o pacote de fala em português nas configurações do Windows.",
                )
            )
        if result.returncode != 0:
            raise VoiceError(self._failure_message(result, "Não consegui acessar o microfone."))
        recognized = " ".join(result.stdout.split()).strip()
        if not recognized:
            raise VoiceTimeoutError("Não ouvi nenhum comando. Voltando ao teclado.")
        return recognized

    def _ensure_available(self) -> None:
        if not self.capabilities().output_available:
            raise VoiceUnavailableError(self.capabilities().detail)

    def _run(
        self,
        script: str,
        *,
        input_text: str = "",
        environment: dict[str, str],
        timeout: int,
    ) -> subprocess.CompletedProcess[str]:
        import os

        env = os.environ.copy()
        env.update(environment)
        try:
            return self._runner(
                [
                    str(self.executable),
                    "-NoProfile",
                    "-NonInteractive",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    script,
                ],
                input=input_text,
                text=True,
                capture_output=True,
                timeout=timeout,
                env=env,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise VoiceTimeoutError("O mecanismo de voz excedeu o tempo de resposta.") from exc
        except OSError as exc:
            raise VoiceUnavailableError("Não consegui iniciar o mecanismo de voz do Windows.") from exc

    @staticmethod
    def _failure_message(result: subprocess.CompletedProcess[str], fallback: str) -> str:
        detail = " ".join((result.stderr or "").split()).strip()
        return detail or fallback


class VoiceService:
    """Fachada da voz, independente da interface do terminal."""

    def __init__(
        self,
        backend: VoiceBackend,
        *,
        language: str = "pt-BR",
        input_timeout: int = 8,
        rate: int = 0,
        volume: int = 100,
    ) -> None:
        self.backend = backend
        self.language = language
        self.input_timeout = input_timeout
        self.rate = rate
        self.volume = volume

    @classmethod
    def local_default(
        cls,
        *,
        language: str = "pt-BR",
        input_timeout: int = 8,
        rate: int = 0,
        volume: int = 100,
    ) -> VoiceService:
        return cls(
            WindowsSpeechBackend(),
            language=language,
            input_timeout=input_timeout,
            rate=rate,
            volume=volume,
        )

    def capabilities(self) -> VoiceCapabilities:
        return self.backend.capabilities()

    def speak(self, text: str) -> None:
        self.backend.speak(
            text,
            language=self.language,
            rate=self.rate,
            volume=self.volume,
        )

    def listen_once(self) -> str:
        return self.backend.listen_once(
            language=self.language,
            timeout=self.input_timeout,
        )
