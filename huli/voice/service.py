"""Entrada e saída de voz local da Huli no Windows."""

from __future__ import annotations

from dataclasses import dataclass
import platform
import json
from pathlib import Path
import shutil
import subprocess
from typing import Callable, Protocol


class VoiceError(RuntimeError):
    """Falha controlada da interface de voz."""


class VoiceUnavailableError(VoiceError):
    """O sistema não oferece o recurso de voz solicitado."""


class VoiceTimeoutError(VoiceError):
    """Nenhuma fala foi reconhecida no tempo configurado."""


class VoiceCancelledError(VoiceError):
    """A escuta foi interrompida localmente antes de produzir um comando."""


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
$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
Add-Type -AssemblyName System.Speech
$text = [Console]::In.ReadToEnd()
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$voice = $synth.GetInstalledVoices() |
    Where-Object { $_.Enabled -and $_.VoiceInfo.Culture.Name -eq $env:HULI_SPEECH_LANGUAGE } |
    Select-Object -First 1
if ($null -eq $voice) { throw 'Nenhuma voz instalada para o idioma solicitado.' }
$synth.SelectVoice($voice.VoiceInfo.Name)
$synth.Rate = [int]$env:HULI_SPEECH_RATE
$synth.Volume = [int]$env:HULI_SPEECH_VOLUME
try { $synth.Speak($text) } finally { $synth.Dispose() }
""".strip()

    _LISTEN_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
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

    _PROBE_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    $outputVoices = @($synth.GetInstalledVoices() | Where-Object {
        $_.Enabled -and $_.VoiceInfo.Culture.Name -eq $env:HULI_SPEECH_LANGUAGE
    })
    $inputEngines = @([System.Speech.Recognition.SpeechRecognitionEngine]::InstalledRecognizers() | Where-Object {
        $_.Culture.Name -eq $env:HULI_SPEECH_LANGUAGE
    })
    @{output_available=($outputVoices.Count -gt 0); input_available=($inputEngines.Count -gt 0)} | ConvertTo-Json -Compress
} finally { $synth.Dispose() }
""".strip()

    def __init__(
        self,
        *,
        executable: str | None = None,
        platform_name: str | None = None,
        runner: Runner = subprocess.run,
        language: str = "pt-BR",
    ) -> None:
        self.platform_name = platform_name or platform.system()
        self.executable = executable or shutil.which("powershell") or shutil.which("pwsh")
        self._runner = runner
        self.language = language
        self._capabilities: VoiceCapabilities | None = None

    def capabilities(self) -> VoiceCapabilities:
        if self._capabilities is not None:
            return self._capabilities
        if self.platform_name != "Windows" or not self.executable:
            return VoiceCapabilities(False, False, "windows-system-speech", "Requer Windows e PowerShell.")
        try:
            result = self._run(self._PROBE_SCRIPT, environment={"HULI_SPEECH_LANGUAGE": self.language}, timeout=15)
            if result.returncode != 0:
                raise VoiceUnavailableError(self._failure_message(result, "Falha ao consultar System.Speech."))
            info = json.loads(result.stdout.lstrip("\ufeff"))
            output = info.get("output_available") is True
            input_ = info.get("input_available") is True
            detail = f"Fala {self.language}: {'disponível' if output else 'ausente'}; reconhecimento Windows: {'disponível' if input_ else 'ausente'}."
            self._capabilities = VoiceCapabilities(output, input_, "windows-system-speech", detail)
        except (VoiceError, ValueError, AttributeError) as exc:
            return VoiceCapabilities(False, False, "windows-system-speech", f"Não consegui verificar os motores de voz: {exc}")
        return self._capabilities

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
        if self.platform_name != "Windows" or not self.executable:
            raise VoiceUnavailableError("A voz do Windows requer Windows e PowerShell.")

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
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                timeout=timeout,
                env=env,
                check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
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
        input_provider: str = "auto",
        model_path: Path | None = None,
        input_device: str | int | None = None,
    ) -> VoiceService:
        from huli.voice.local import LocalVoiceBackend

        return cls(
            LocalVoiceBackend(language=language, input_provider=input_provider,
                              model_path=model_path, input_device=input_device),
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

    def listen_once(self, *, timeout: int | None = None, cancel_event=None) -> str:
        resolved_timeout = timeout or self.input_timeout
        if cancel_event is not None:
            cancelable = getattr(self.backend, "listen_cancelable", None)
            if cancelable is not None:
                return cancelable(
                    language=self.language,
                    timeout=resolved_timeout,
                    cancel_event=cancel_event,
                )
        return self.backend.listen_once(language=self.language, timeout=resolved_timeout)

    def listen_wake_once(
        self,
        *,
        timeout: int,
        cancel_event=None,
        aliases: tuple[str, ...] = (),
    ) -> str:
        """Obtém a transcrição bruta usada somente pelo detector de ativação."""
        listener = getattr(self.backend, "listen_wake_once", None)
        if listener is not None:
            return listener(
                language=self.language,
                timeout=timeout,
                cancel_event=cancel_event,
                aliases=aliases,
            )
        return self.listen_once(timeout=timeout, cancel_event=cancel_event)

    def listen_calibration_once(self, *, timeout: int, cancel_event=None) -> str:
        """Valida uma amostra fonética não executável do nome."""
        listener = getattr(self.backend, "listen_calibration_once", None)
        if listener is not None:
            return listener(
                language=self.language,
                timeout=timeout,
                cancel_event=cancel_event,
            )
        return self.listen_once(timeout=timeout, cancel_event=cancel_event)

    def prepare_input(self) -> None:
        """Carrega recursos antes de avisar que o usuário já pode falar."""
        prepare = getattr(self.backend, "prepare_input", None)
        if prepare is not None:
            prepare()
