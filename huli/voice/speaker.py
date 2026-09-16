"""Verificação local de locutor com x-vectors Vosk; nenhum áudio é persistido."""
from __future__ import annotations

from base64 import b64decode, b64encode
from dataclasses import dataclass
import json
import math
from pathlib import Path
import threading
from typing import Any, Iterable

from huli.security.encrypted_file import write_envelope
from huli.security.os_protection import OSKeyProtector, OSProtectionError, default_os_key_protector
from huli.voice.service import VoiceError, VoiceIdentityError, VoiceUnavailableError

_PROFILE_FORMAT = "huli-owner-voice-profile"
_PROFILE_VERSION = 2
_MODEL_ID = "vosk-model-spk-0.4"
_DEFAULT_THRESHOLD = 0.75
_DIMENSIONS = 128


def _unit(values) -> list[float]:
    try:
        result = [float(value) for value in values]
        if len(result) != _DIMENSIONS or not all(math.isfinite(v) for v in result):
            raise ValueError()
        norm = math.sqrt(sum(v * v for v in result))
        if norm < 1e-9:
            raise ValueError()
        return [v / norm for v in result]
    except (TypeError, ValueError, OverflowError) as exc:
        raise VoiceError("Assinatura vocal inválida. Cadastre sua voz novamente.") from exc


def _cosine(left, right) -> float:
    return sum(a * b for a, b in zip(_unit(left), _unit(right)))


@dataclass(frozen=True, slots=True)
class SpeakerEnrollment:
    samples: int
    consistency: float


class SpeakerProfileStore:
    """Características biométricas protegidas pelo Windows, separadas do diário."""

    def __init__(self, path: Path, protector: OSKeyProtector | None = None) -> None:
        self.path = Path(path)
        self.protector = protector or default_os_key_protector()

    def exists(self) -> bool:
        return self.path.is_file()

    def load(self) -> dict[str, Any] | None:
        try:
            envelope = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(envelope, dict) or envelope.get("format") != _PROFILE_FORMAT:
                raise ValueError()
            protected = b64decode(envelope["protected_profile"], validate=True)
            payload = json.loads(self.protector.unprotect(protected).decode("utf-8"))
            if not isinstance(payload, dict) or payload.get("version") != _PROFILE_VERSION:
                raise ValueError()
            if payload.get("model") != _MODEL_ID:
                raise ValueError()
            _unit(payload.get("centroid"))
            templates = payload.get("templates")
            if not isinstance(templates, list) or len(templates) != 5:
                raise ValueError()
            for template in templates:
                _unit(template)
            threshold = float(payload["threshold"])
            if not math.isfinite(threshold) or not 0.75 <= threshold <= 0.95:
                raise ValueError()
            return payload
        except FileNotFoundError:
            return None
        except (KeyError, TypeError, OSError, OSProtectionError, ValueError) as exc:
            raise VoiceUnavailableError(
                "Perfil vocal ausente, incompatível ou ilegível. Use ‘Minha voz’ para cadastrar novamente."
            ) from exc

    def save(self, payload: dict[str, Any]) -> None:
        if self.protector.name != "windows-dpapi-current-user":
            raise VoiceUnavailableError("O perfil vocal exige a proteção da conta do Windows.")
        try:
            protected = self.protector.protect(json.dumps(payload, allow_nan=False).encode("utf-8"))
            write_envelope(self.path, {
                "format": _PROFILE_FORMAT,
                "protection": self.protector.name,
                "protected_profile": b64encode(protected).decode("ascii"),
            })
        except (OSProtectionError, OSError, ValueError) as exc:
            raise VoiceError("Não consegui salvar o perfil vocal protegido.") from exc


class VoskSpeakerEncoder:
    """Modelo treinado de identificação de locutor; Whisper continua transcrevendo."""

    def __init__(self, language_model: Path, speaker_model: Path) -> None:
        self.language_model = Path(language_model)
        self.speaker_model = Path(speaker_model)
        self._model = None
        self._speaker = None
        self._lock = threading.Lock()

    def prepare(self) -> None:
        with self._lock:
            if self._speaker is not None:
                return
            if not (self.speaker_model / "final.ext.raw").is_file():
                raise VoiceUnavailableError("Modelo de identificação vocal ausente em models/vosk-model-spk-0.4.")
            try:
                from vosk import Model, SpkModel
                self._model = Model(str(self.language_model))
                self._speaker = SpkModel(str(self.speaker_model))
            except Exception as exc:
                raise VoiceUnavailableError("Não consegui carregar o modelo local de identificação vocal.") from exc

    def __call__(self, pcm: bytes) -> list[float]:
        if len(pcm) < 16000 * 2 * 1.5 or len(pcm) % 2:
            raise VoiceIdentityError("Fale uma frase mais longa para conferir sua voz; comando ignorado.")
        self.prepare()
        try:
            from vosk import KaldiRecognizer
            with self._lock:
                recognizer = KaldiRecognizer(self._model, 16000)
                recognizer.SetSpkModel(self._speaker)
                # Um único lote conserva o segmento inteiro para o x-vector.
                recognizer.AcceptWaveform(pcm)
                result = json.loads(recognizer.FinalResult())
            if result.get("spk_frames", 0) < 100 or not result.get("spk"):
                raise VoiceIdentityError("Não houve fala nítida suficiente para conferir sua voz.")
            return _unit(result["spk"])
        except VoiceError:
            raise
        except Exception as exc:
            raise VoiceUnavailableError("Falha ao conferir a voz; nenhum comando foi liberado.") from exc


class SpeakerVerifier:
    """Compara cada comando com cinco referências; não autentica a sessão ou o cofre."""

    def __init__(self, store: SpeakerProfileStore, *, enabled: bool = False,
                 threshold: float = _DEFAULT_THRESHOLD, encoder=None) -> None:
        from huli.infrastructure.config import APP_ROOT
        self.store = store
        self.enabled = bool(enabled)
        self.threshold = max(0.75, min(0.95, float(threshold)))
        self.encoder = encoder or VoskSpeakerEncoder(
            APP_ROOT / "models" / "vosk-pt", APP_ROOT / "models" / _MODEL_ID
        )

    @property
    def ready(self) -> bool:
        try:
            return self.store.load() is not None
        except VoiceError:
            return False

    def prepare(self) -> None:
        prepare = getattr(self.encoder, "prepare", None)
        if prepare:
            prepare()

    def enroll(self, samples: Iterable[bytes]) -> SpeakerEnrollment:
        samples = list(samples)
        if len(samples) != 5:
            raise VoiceError("São necessárias cinco amostras completas da sua voz.")
        embeddings = [_unit(self.encoder(sample)) for sample in samples]
        centroid = _unit([sum(e[i] for e in embeddings) for i in range(_DIMENSIONS)])
        # Cada amostra precisa combinar também com as demais, não só consigo.
        scores = [
            sum(_cosine(embedding, other) for j, other in enumerate(embeddings) if j != i) / 4
            for i, embedding in enumerate(embeddings)
        ]
        consistency = min(scores)
        if consistency < 0.70:
            raise VoiceError("As amostras variaram demais. Repita as cinco frases em tom natural.")
        self.store.save({
            "version": _PROFILE_VERSION, "model": _MODEL_ID,
            "threshold": self.threshold, "centroid": centroid, "templates": embeddings,
        })
        return SpeakerEnrollment(5, consistency)

    def verify(self, pcm: bytes) -> float:
        if not self.enabled:
            return 1.0
        profile = self.store.load()
        if profile is None:
            raise VoiceUnavailableError("Cadastre a voz no botão ‘Minha voz’ antes de usar comandos falados.")
        candidate = _unit(self.encoder(pcm))
        score = _cosine(candidate, profile["centroid"])
        matches = sum(_cosine(candidate, template) >= 0.70 for template in profile["templates"])
        if score < max(self.threshold, profile["threshold"]) or matches < 3:
            raise VoiceIdentityError("Voz não confirmada como a do Rony; comando ignorado.")
        return score
