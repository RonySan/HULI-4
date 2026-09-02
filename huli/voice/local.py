"""Escuta Vosk offline combinada à síntese instalada no Windows.

O modelo é sempre um caminho explícito: nunca é baixado durante a conversa.
Áudio fica em uma fila limitada em RAM e não é salvo ou enviado a serviços.
"""

from __future__ import annotations

from array import array
import importlib
import json
from pathlib import Path
import queue
import threading
import time

from huli.brain.normalization import normalize_text
from huli.voice.service import (
    VoiceCancelledError, VoiceCapabilities, VoiceError, VoiceTimeoutError, VoiceUnavailableError,
    WindowsSpeechBackend,
)
from huli.voice.transcript import (
    is_spoken_vocative,
    normalize_spoken_vocative,
    resolve_safe_voice_query,
)


class PhoneticWakeInput:
    """Detector de palavra-chave por fonemas, sem converter Huli em outra palavra."""

    sample_rate = 16_000

    def __init__(self, device: str | int | None = None) -> None:
        self.device = device
        self._decoder = None
        self._decoder_lock = threading.Lock()
        self._listen_lock = threading.Lock()

    @staticmethod
    def _dependencies():
        try:
            return importlib.import_module("pocketsphinx"), importlib.import_module(
                "sounddevice"
            )
        except (ImportError, OSError) as exc:
            raise VoiceUnavailableError(
                "Detector fonético ausente. Execute INSTALAR_VOZ_LOCAL.bat."
            ) from exc

    def check(self) -> str:
        self._dependencies()
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
                "Não encontrei um microfone utilizável para a ativação fonética."
            ) from exc
        return str(info["name"])

    def prepare(self) -> None:
        pocketsphinx, _ = self._dependencies()
        with self._decoder_lock:
            if self._decoder is not None:
                return
            try:
                decoder = pocketsphinx.Decoder(
                    lm=None,
                    samprate=self.sample_rate,
                    loglevel="ERROR",
                )
                decoder.add_word("HULI", "HH UW L IY", False)
                decoder.add_word("RULI", "R UW L IY", False)
                keywords = Path(__file__).parent / "resources" / "huli.kws"
                decoder.add_kws("huli-wake", str(keywords))
                decoder.activate_search("huli-wake")
                self._decoder = decoder
            except Exception as exc:
                raise VoiceUnavailableError(
                    "Não consegui preparar o detector fonético Huli/Ruli."
                ) from exc

    @staticmethod
    def _resample(block: bytes, source_rate: int, target_rate: int) -> bytes:
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

    def listen_once(self, *, timeout: int, cancel_event=None) -> str:
        if not self._listen_lock.acquire(blocking=False):
            raise VoiceError("O microfone já está sendo usado pela Huli.")
        decoder_started = False
        try:
            if cancel_event is not None and cancel_event.is_set():
                raise VoiceCancelledError("Escuta cancelada.")
            self.prepare()
            _, sd = self._dependencies()
            self.check()
            info = sd.query_devices(self.device, "input")
            source_rate = int(info["default_samplerate"])
            audio: queue.Queue[bytes] = queue.Queue(maxsize=64)
            overflow = threading.Event()

            def receive(data, frames, timing, status):
                if status:
                    overflow.set()
                try:
                    audio.put_nowait(bytes(data))
                except queue.Full:
                    overflow.set()

            decoder = self._decoder
            decoder.start_utt()
            decoder_started = True
            deadline = time.monotonic() + timeout
            with sd.RawInputStream(
                samplerate=source_rate,
                blocksize=max(1, source_rate // 10),
                device=self.device,
                dtype="int16",
                channels=1,
                callback=receive,
            ):
                while time.monotonic() < deadline:
                    if cancel_event is not None and cancel_event.is_set():
                        raise VoiceCancelledError("Escuta cancelada.")
                    if overflow.is_set():
                        raise VoiceError(
                            "Houve perda de áudio na ativação; tente novamente."
                        )
                    try:
                        block = audio.get(
                            timeout=min(
                                0.2,
                                max(0.01, deadline - time.monotonic()),
                            )
                        )
                    except queue.Empty:
                        continue
                    converted = self._resample(
                        block,
                        source_rate,
                        self.sample_rate,
                    )
                    decoder.process_raw(converted, False, False)
                    hypothesis = decoder.hyp()
                    detected = (
                        set(hypothesis.hypstr.upper().split())
                        if hypothesis
                        else set()
                    )
                    if detected.intersection({"HULI", "RULI"}):
                        return "huli"
            raise VoiceTimeoutError("Não reconheci o chamado fonético Huli/Ruli.")
        except (VoiceError, KeyboardInterrupt):
            raise
        except Exception as exc:
            raise VoiceError(
                "Falha no detector fonético. Confira o microfone e tente novamente."
            ) from exc
        finally:
            if decoder_started and self._decoder is not None:
                self._decoder.end_utt()
            self._listen_lock.release()


class VoskInput:
    def __init__(self, model_path: Path, device: str | int | None = None) -> None:
        self.model_path = Path(model_path)
        self.device = device
        self._model = None
        self._model_lock = threading.Lock()
        self._listen_lock = threading.Lock()

    def _dependencies(self):
        try:
            return importlib.import_module("vosk"), importlib.import_module("sounddevice")
        except (ImportError, OSError) as exc:
            raise VoiceUnavailableError("Instale os recursos locais com INSTALAR_VOZ_LOCAL.bat.") from exc

    def _check_model(self) -> None:
        if not any(path.is_file() for path in (self.model_path / "final.mdl", self.model_path / "am" / "final.mdl")):
            raise VoiceUnavailableError(f"Modelo português ausente em {self.model_path}. Execute INSTALAR_VOZ_LOCAL.bat.")

    def check(self) -> str:
        self._check_model()
        _, sd = self._dependencies()
        try:
            info = sd.query_devices(self.device, "input")
            rate = int(info["default_samplerate"])
            sd.check_input_settings(device=self.device, channels=1, dtype="int16", samplerate=rate)
        except Exception as exc:
            raise VoiceUnavailableError("Não encontrei um microfone utilizável. Confira permissões e HULI_VOICE_INPUT_DEVICE.") from exc
        return str(info["name"])

    def prepare(self) -> None:
        self._check_model()
        vosk, _ = self._dependencies()
        with self._model_lock:
            if self._model is None:
                try:
                    vosk.SetLogLevel(-1)
                    self._model = vosk.Model(str(self.model_path))
                except Exception as exc:
                    raise VoiceUnavailableError("Não consegui carregar o modelo local. Reinstale o modelo português.") from exc

    @staticmethod
    def _result_text(
        payload: str,
        *,
        allow_wake_word: bool = False,
        wake_aliases: tuple[str, ...] = (),
        calibration: bool = False,
    ) -> str:
        result = json.loads(payload)
        text = " ".join(str(result.get("text", "")).split())
        words = result.get("result", [])
        if words and not calibration:
            confidence = sum(float(word.get("conf", 0)) for word in words) / len(words)
            if confidence < 0.65:
                safe_wake = (
                    allow_wake_word
                    and confidence >= 0.45
                    and (
                        is_spoken_vocative(text)
                        or normalize_text(text) in set(wake_aliases)
                    )
                )
                if not safe_wake and (
                    confidence < 0.50 or resolve_safe_voice_query(text) is None
                ):
                    raise VoiceError("Não entendi com segurança. Repita a frase ou use o teclado; não executei o comando.")
        return text

    def listen_once(self, *, language: str, timeout: int, cancel_event=None,
                    normalize_transcript: bool = True,
                    wake_aliases: tuple[str, ...] = (),
                    calibration: bool = False) -> str:
        if language.casefold() != "pt-br":
            raise VoiceUnavailableError("O modelo desta instalação é português do Brasil (pt-BR).")
        if not self._listen_lock.acquire(blocking=False):
            raise VoiceError("O microfone já está sendo usado pela Huli.")
        try:
            if cancel_event is not None and cancel_event.is_set():
                raise VoiceCancelledError("Escuta cancelada.")
            self.prepare()
            vosk, sd = self._dependencies()
            self.check()
            info = sd.query_devices(self.device, "input")
            rate = int(info["default_samplerate"])
            audio: queue.Queue[bytes] = queue.Queue(maxsize=64)
            overflow = threading.Event()

            def receive(data, frames, timing, status):
                if status:
                    overflow.set()
                try:
                    audio.put_nowait(bytes(data))
                except queue.Full:
                    overflow.set()

            recognizer = vosk.KaldiRecognizer(self._model, rate)
            recognizer.SetWords(True)
            deadline = time.monotonic() + timeout
            pending_vocative: str | None = None
            with sd.RawInputStream(samplerate=rate, blocksize=max(1, rate // 5),
                                   device=self.device, dtype="int16", channels=1, callback=receive):
                while time.monotonic() < deadline:
                    if cancel_event is not None and cancel_event.is_set():
                        raise VoiceCancelledError("Escuta cancelada.")
                    if overflow.is_set():
                        raise VoiceError("Houve perda de áudio. Repita o comando; nada foi executado.")
                    try:
                        block = audio.get(timeout=min(0.2, max(0.01, deadline - time.monotonic())))
                    except queue.Empty:
                        continue
                    if recognizer.AcceptWaveform(block):
                        text = self._result_text(
                            recognizer.Result(),
                            allow_wake_word=not normalize_transcript,
                            wake_aliases=wake_aliases,
                            calibration=calibration,
                        )
                        if text:
                            if normalize_transcript and is_spoken_vocative(text):
                                # Uma pausa depois do nome não encerra a escuta.
                                # Repetir o chamado não renova o prazo original.
                                pending_vocative = text
                                continue
                            if pending_vocative:
                                text = f"{pending_vocative} {text}"
                            return normalize_spoken_vocative(text) if normalize_transcript else text
            # Uma frase cortada pelo limite nunca vira um comando executável.
            if pending_vocative:
                raise VoiceTimeoutError("Só entendi o chamado, sem a pergunta completa. Voltando ao teclado; use ouvir para tentar novamente.")
            raise VoiceTimeoutError("Não recebi uma frase completa. Voltando ao teclado; diga mais perto do microfone ou aumente o tempo de escuta.")
        except (VoiceError, KeyboardInterrupt):
            raise
        except Exception as exc:
            raise VoiceError("Falha na escuta local. Confira o microfone e suas permissões no Windows.") from exc
        finally:
            self._listen_lock.release()


class LocalVoiceBackend:
    def __init__(self, *, language: str = "pt-BR", input_provider: str = "auto",
                 model_path: Path | None = None, input_device: str | int | None = None) -> None:
        from huli.infrastructure.config import APP_ROOT

        self.language = language
        self.input_provider = input_provider
        self.synthesis = WindowsSpeechBackend(language=language)
        self.vosk = VoskInput(model_path or APP_ROOT / "models" / "vosk-pt", input_device)
        self.phonetic_wake = PhoneticWakeInput(input_device)

    def capabilities(self) -> VoiceCapabilities:
        native = self.synthesis.capabilities()
        if self.input_provider == "windows":
            return native
        try:
            if self.language.casefold() != "pt-br":
                raise VoiceUnavailableError("O modelo Vosk configurado é pt-BR.")
            microphone = self.vosk.check()
            try:
                self.phonetic_wake.check()
                wake_detail = " Detector fonético Huli/Ruli: pronto."
            except VoiceError as exc:
                wake_detail = f" Detector fonético: {exc}"
            return VoiceCapabilities(native.output_available, True, "windows-tts+vosk-offline", f"{native.detail} Escuta Vosk: pronta para teste; microfone: {microphone}.{wake_detail}")
        except VoiceError as exc:
            if self.input_provider == "auto" and native.input_available:
                return native
            return VoiceCapabilities(native.output_available, False, "windows-tts+vosk-offline", f"{native.detail} Escuta Vosk: {exc}")

    def speak(self, text: str, *, language: str, rate: int, volume: int) -> None:
        self.synthesis.speak(text, language=language, rate=rate, volume=volume)

    def prepare_input(self) -> None:
        capabilities = self.capabilities()
        if not capabilities.input_available:
            raise VoiceUnavailableError(capabilities.detail)
        if capabilities.provider == "windows-tts+vosk-offline":
            self.vosk.prepare()

    def listen_once(self, *, language: str, timeout: int) -> str:
        capabilities = self.capabilities()
        if not capabilities.input_available:
            raise VoiceUnavailableError(capabilities.detail)
        if capabilities.provider == "windows-system-speech":
            return self.synthesis.listen_once(language=language, timeout=timeout)
        return self.vosk.listen_once(language=language, timeout=timeout)

    def listen_cancelable(self, *, language: str, timeout: int, cancel_event) -> str:
        capabilities = self.capabilities()
        if not capabilities.input_available:
            raise VoiceUnavailableError(capabilities.detail)
        if capabilities.provider == "windows-system-speech":
            return self.synthesis.listen_once(language=language, timeout=timeout)
        return self.vosk.listen_once(
            language=language,
            timeout=timeout,
            cancel_event=cancel_event,
        )

    def listen_wake_once(
        self,
        *,
        language: str,
        timeout: int,
        cancel_event=None,
        aliases: tuple[str, ...] = (),
    ) -> str:
        if language.casefold() != "pt-br":
            raise VoiceUnavailableError("A ativação fonética está configurada para pt-BR.")
        return self.phonetic_wake.listen_once(
            timeout=timeout,
            cancel_event=cancel_event,
        )

    def listen_calibration_once(
        self,
        *,
        language: str,
        timeout: int,
        cancel_event=None,
    ) -> str:
        if language.casefold() != "pt-br":
            raise VoiceUnavailableError("A calibração fonética está configurada para pt-BR.")
        return self.phonetic_wake.listen_once(
            timeout=timeout,
            cancel_event=cancel_event,
        )
