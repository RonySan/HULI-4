"""Testa bloqueios e persistência; vetores simulados não medem precisão biométrica."""
from pathlib import Path
from types import SimpleNamespace
import threading
import pytest
from huli.voice import VoiceError, VoiceIdentityError, VoiceUnavailableError, VoiceCancelledError
from huli.voice.speaker import SpeakerProfileStore, SpeakerVerifier, VoskSpeakerEncoder
from huli.voice.whisper import FasterWhisperInput
from huli.voice.local import LocalVoiceBackend


class FakeProtector:
    name = "windows-dpapi-current-user"

    def protect(self, data):
        return b"protected:" + data[::-1]

    def unprotect(self, data):
        return data.removeprefix(b"protected:")[::-1]


def vector(position=0):
    return [1.0 if i == position else 0.0 for i in range(128)]


def verifier(tmp_path, encoder=None):
    return SpeakerVerifier(
        SpeakerProfileStore(tmp_path / "profile.json", FakeProtector()),
        enabled=True, encoder=encoder or (lambda pcm: vector(0 if pcm == b"owner" else 1))
    )


def test_profile_encryption_and_restart(tmp_path):
    check = verifier(tmp_path)
    assert check.enroll([b"owner"] * 5).samples == 5
    assert "centroid" not in check.store.path.read_text()
    assert verifier(tmp_path).verify(b"owner") == pytest.approx(1)


def test_impostor_is_rejected(tmp_path):
    check = verifier(tmp_path)
    check.enroll([b"owner"] * 5)
    with pytest.raises(VoiceIdentityError):
        check.verify(b"other")


def test_missing_and_corrupted_profiles_block(tmp_path):
    check = verifier(tmp_path)
    with pytest.raises(VoiceUnavailableError):
        check.verify(b"owner")
    check.store.path.write_text("{}")
    with pytest.raises(VoiceUnavailableError):
        check.verify(b"owner")


@pytest.mark.parametrize("bad", [[], [float("nan")]*128, [0]*128, [float("inf")]*128])
def test_invalid_vectors_never_authorize(tmp_path, bad):
    check = verifier(tmp_path)
    check.enroll([b"owner"] * 5)
    check.encoder = lambda pcm: bad
    with pytest.raises(VoiceError):
        check.verify(b"owner")


def test_inconsistent_enrollment_preserves_existing_profile(tmp_path):
    check = verifier(tmp_path)
    check.enroll([b"owner"] * 5)
    original = check.store.path.read_bytes()
    with pytest.raises(VoiceError):
        check.enroll([b"owner", b"other", b"other", b"owner", b"owner"])
    assert check.store.path.read_bytes() == original


def test_disabled_filter_does_not_read_profile(tmp_path):
    check = verifier(tmp_path)
    check.enabled = False
    assert check.verify(b"") == 1


def test_whisper_checks_identity_before_transcription(tmp_path, monkeypatch):
    def reject(pcm):
        raise VoiceIdentityError("não confirmado")
    backend = FasterWhisperInput(tmp_path, speaker_verifier=SimpleNamespace(verify=reject))
    monkeypatch.setattr(backend, "prepare", lambda: None)
    monkeypatch.setattr(backend, "_capture_phrase", lambda **kw: b"audio")
    transcribed = []
    monkeypatch.setattr(backend, "_transcribe", lambda *a, **kw: transcribed.append(True))
    with pytest.raises(VoiceIdentityError):
        backend.listen_once(language="pt-BR", timeout=5)
    assert not transcribed
    assert not backend._listen_lock.locked()


def test_fallback_engine_cannot_bypass_filter(tmp_path, monkeypatch):
    backend = LocalVoiceBackend(speaker_verification_enabled=True, speaker_profile_path=tmp_path/"p.json")
    monkeypatch.setattr(backend, "_selected_input", lambda: backend.vosk)
    with pytest.raises(VoiceUnavailableError):
        backend.listen_once(language="pt-BR", timeout=5)
    with pytest.raises(VoiceUnavailableError):
        backend.listen_cancelable(language="pt-BR", timeout=5, cancel_event=threading.Event())


def test_enrollment_capture_cancelled_before_microphone(tmp_path):
    backend = FasterWhisperInput(tmp_path)
    cancelled = threading.Event()
    cancelled.set()
    with pytest.raises(VoiceCancelledError):
        backend.capture_speaker_sample(timeout=5, cancel_event=cancelled)
    assert not backend._listen_lock.locked()


def test_installed_speaker_model_rejects_silence():
    root = Path(__file__).resolve().parents[1]
    if not (root/"models/vosk-model-spk-0.4/final.ext.raw").is_file():
        pytest.skip("modelo opcional não instalado")
    pytest.importorskip("vosk")
    encoder = VoskSpeakerEncoder(root/"models/vosk-pt", root/"models/vosk-model-spk-0.4")
    with pytest.raises(VoiceIdentityError):
        encoder(bytes(16000*2*5))
