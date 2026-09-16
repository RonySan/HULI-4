"""Reconhecimento local de comandos com Faster Whisper.

O áudio permanece em memória, é encerrado após uma pequena pausa e nunca é
gravado em disco. O modelo deve ser instalado explicitamente antes do uso.
"""

from __future__ import annotations

from array import array
from collections import deque
import importlib
from io import BytesIO
import math
import os
from pathlib import Path
import queue
import threading
import time
import wave

from huli.voice.service import (
    VoiceCancelledError,
    VoiceError,
    VoiceTimeoutError,
    VoiceUnavailableError,
)
from huli.voice.speaker import SpeakerVerifier


_COMMAND_PROMPT = (
    "Huli, assistente pessoal em português do Brasil. Comandos comuns: abrir Spotify, "
    "abrir calculadora, tocar minhas favoritas, Google Calendar, agenda do Google, "
    "agenda de hoje, agenda desta semana, compromissos, criar evento no Google, tarefas, "
    "lembretes, lista de compras, hábitos, temporizador, que horas são."
)


def _amplify_pcm16(block: bytes, gain: float) -> bytes:
    if gain == 1.0 or not block:
        return block
    samples = array("h")
    samples.frombytes(block)
    for index, sample in enumerate(samples):
        samples[index] = max(-32_768, min(32_767, round(sample * gain)))
    return samples.tobytes()


def _resample_pcm16(block: bytes, source_rate: int, target_rate: int) -> bytes:
    if source_rate == target_rate:
        return block
    samples = array("h")
    samples.frombytes(block)
    if not samples:
        return b""
    size = max(1, int(len(samples) * target_rate / source_rate))
    converted = array(
        "h",
        (
            samples[min(len(samples) - 1, int(index * source_rate / target_rate))]
            for index in range(size)
        ),
    )
    return converted.tobytes()


def _signal_level(block: bytes) -> tuple[float, int]:
    samples = array("h")
    samples.frombytes(block)
    if not samples:
        return 0.0, 0
    peak = max(abs(sample) for sample in samples)
    rms = math.sqrt(sum(sample * sample for sample in samples) / len(samples))
    return rms, peak


class FasterWhisperInput:
    """Captura uma frase inteira e a transcreve localmente em pt-BR."""

    sample_rate = 16_000
    _REQUIRED_MODEL_FILES = ("model.bin", "config.json", "tokenizer.json")

    def __init__(
        self,
        model_path: Path,
        device: str | int | None = None,
        *,
        input_gain: float = 1.0,
        trailing_silence_seconds: float = 1.1,
        speaker_verifier: SpeakerVerifier | None = None,
    ) -> None:
        self.model_path = Path(model_path)
        self.device = device
        self.input_gain = input_gain
        self.trailing_silence_seconds = max(0.6, trailing_silence_seconds)
        self.speaker_verifier = speaker_verifier
        self._model = None
        self._model_lock = threading.Lock()
        self._listen_lock = threading.Lock()

    @staticmethod
    def _dependencies():
        try:
            return importlib.import_module("faster_whisper"), importlib.import_module(
                "sounddevice"
            )
        except (ImportError, OSError) as exc:
            raise VoiceUnavailableError(
                "Whisper local ausente. Execute INSTALAR_VOZ_MELHORADA.bat."
            ) from exc

    def _check_model(self) -> None:
        if not all((self.model_path / name).is_file() for name in self._REQUIRED_MODEL_FILES):
            raise VoiceUnavailableError(
                "Modelo Whisper português ausente. Execute INSTALAR_VOZ_MELHORADA.bat."
            )

    def check(self) -> str:
        self._check_model()
        _, sd = self._dependencies()
        try:
            info = sd.query_devices(self.device, "input")
            rate = int(info["default_samplerate"])
            sd.check_input_settings(
                device=self.device,
                channels=1,
                dtype="int16",
                samplerate=rate,
            )
        except Exception as exc:
            raise VoiceUnavailableError(
                "Não encontrei um microfone utilizável para o Whisper local."
            ) from exc
        return str(info["name"])

    def prepare(self) -> None:
        self._check_model()
        faster_whisper, _ = self._dependencies()
        with self._model_lock:
            if self._model is not None:
                return
            try:
                self._model = faster_whisper.WhisperModel(
                    str(self.model_path),
                    device="cpu",
                    compute_type="int8",
                    cpu_threads=max(1, min(4, os.cpu_count() or 1)),
                )
            except Exception as exc:
                raise VoiceUnavailableError(
                    "Não consegui carregar o modelo Whisper local. Reinstale a voz melhorada."
                ) from exc

    def listen_once(self, *, language: str, timeout: int, cancel_event=None) -> str:
        if language.casefold() != "pt-br":
            raise VoiceUnavailableError("O Whisper desta instalação está configurado para pt-BR.")
        if not self._listen_lock.acquire(blocking=False):
            raise VoiceError("O microfone já está sendo usado pela Huli.")
        try:
            if cancel_event is not None and cancel_event.is_set():
                raise VoiceCancelledError("Escuta cancelada.")
            self.prepare()
            pcm = self._capture_phrase(timeout=timeout, cancel_event=cancel_event)
            if cancel_event is not None and cancel_event.is_set():
                raise VoiceCancelledError("Escuta cancelada.")
            if self.speaker_verifier is not None:
                self.speaker_verifier.verify(pcm)
            return self._transcribe(pcm, cancel_event=cancel_event)
        except (VoiceError, KeyboardInterrupt):
            raise
        except Exception as exc:
            raise VoiceError(
                "Falha no reconhecimento Whisper local. Confira o microfone e tente novamente."
            ) from exc
        finally:
            self._listen_lock.release()

    def capture_speaker_sample(self, *, timeout: int, cancel_event=None, on_ready=None) -> bytes:
        """Captura uma amostra não transcrita e sem passar pelo perfil existente."""
        if not self._listen_lock.acquire(blocking=False):
            raise VoiceError("O microfone já está sendo usado pela Huli.")
        try:
            if cancel_event is not None and cancel_event.is_set():
                raise VoiceCancelledError("Escuta cancelada.")
            return self._capture_phrase(timeout=timeout, cancel_event=cancel_event, on_ready=on_ready)
        except (VoiceError, KeyboardInterrupt):
            raise
        except Exception as exc:
            raise VoiceError("Falha ao capturar a amostra do perfil vocal.") from exc
        finally:
            self._listen_lock.release()

    def _capture_phrase(self, *, timeout: int, cancel_event=None, on_ready=None) -> bytes:
        _, sd = self._dependencies()
        self.check()
        info = sd.query_devices(self.device, "input")
        source_rate = int(info["default_samplerate"])
        block_seconds = 0.1
        silence_blocks_needed = max(
            1,
            round(self.trailing_silence_seconds / block_seconds),
        )
        audio: queue.Queue[bytes] = queue.Queue(maxsize=max(64, timeout * 12))
        overflow = threading.Event()

        def receive(data, frames, timing, status):
            if status:
                overflow.set()
            try:
                audio.put_nowait(bytes(data))
            except queue.Full:
                overflow.set()

        deadline = time.monotonic() + timeout
        pre_roll: deque[bytes] = deque(maxlen=4)
        captured: list[bytes] = []
        speech_started = False
        voiced_blocks = 0
        silent_blocks = 0
        with sd.RawInputStream(
            samplerate=source_rate,
            blocksize=max(1, round(source_rate * block_seconds)),
            device=self.device,
            dtype="int16",
            channels=1,
            callback=receive,
        ):
            if on_ready is not None:
                on_ready()
            while time.monotonic() < deadline:
                if cancel_event is not None and cancel_event.is_set():
                    raise VoiceCancelledError("Escuta cancelada.")
                if overflow.is_set():
                    raise VoiceError(
                        "Houve perda de áudio. Repita o comando; nada foi executado."
                    )
                try:
                    raw = audio.get(
                        timeout=min(0.2, max(0.01, deadline - time.monotonic()))
                    )
                except queue.Empty:
                    continue
                amplified = _amplify_pcm16(raw, self.input_gain)
                block = _resample_pcm16(amplified, source_rate, self.sample_rate)
                rms, peak = _signal_level(block)
                has_voice = rms >= 260 or peak >= 1_800
                if not speech_started:
                    pre_roll.append(block)
                    if not has_voice:
                        continue
                    speech_started = True
                    captured.extend(pre_roll)
                    voiced_blocks = 1
                    continue
                captured.append(block)
                if has_voice:
                    voiced_blocks += 1
                    silent_blocks = 0
                else:
                    silent_blocks += 1
                    if voiced_blocks >= 2 and silent_blocks >= silence_blocks_needed:
                        break
        if not speech_started or voiced_blocks < 2:
            raise VoiceTimeoutError(
                "Não ouvi uma frase completa. Fale depois do aviso ‘Estou ouvindo’."
            )
        return b"".join(captured)

    def _transcribe(self, pcm: bytes, *, cancel_event=None) -> str:
        if self._model is None:
            raise VoiceUnavailableError("O modelo Whisper local não foi carregado.")
        audio = BytesIO()
        with wave.open(audio, "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(self.sample_rate)
            output.writeframes(pcm)
        audio.seek(0)
        segments, _info = self._model.transcribe(
            audio,
            language="pt",
            beam_size=5,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 300},
            condition_on_previous_text=False,
            initial_prompt=_COMMAND_PROMPT,
        )
        accepted: list[str] = []
        probabilities: list[float] = []
        for segment in segments:
            if cancel_event is not None and cancel_event.is_set():
                raise VoiceCancelledError("Escuta cancelada.")
            text = " ".join(str(getattr(segment, "text", "")).split())
            if text:
                accepted.append(text)
                probabilities.append(float(getattr(segment, "avg_logprob", 0.0)))
        transcript = " ".join(accepted).strip(" ,.;:!?\t\r\n")
        if not transcript:
            raise VoiceTimeoutError("Não consegui transcrever uma frase completa.")
        if probabilities and sum(probabilities) / len(probabilities) < -1.15:
            raise VoiceError(
                "A transcrição ficou incerta. Repita um pouco mais devagar; nada foi executado."
            )
        return transcript


__all__ = ["FasterWhisperInput"]
