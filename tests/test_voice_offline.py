"""Testes de voz sem ativar hardware, explicitamente distintos do teste real."""

from array import array
import json
import subprocess
from types import SimpleNamespace

import pytest

from huli.brain.intent import IntentEngine, IntentName
from huli.voice import VoiceError, VoiceTimeoutError, VoiceUnavailableError, WindowsSpeechBackend
from huli.voice.local import (
    LocalVoiceBackend,
    PhoneticWakeInput,
    VoskInput,
    amplify_pcm16,
)
from huli.voice.transcript import is_spoken_vocative, normalize_spoken_vocative


def test_windows_probe_does_not_claim_microphone_when_only_tts_exists():
    def runner(*args, **kwargs):
        return subprocess.CompletedProcess(args[0], 0, stdout=json.dumps({"output_available": True, "input_available": False}), stderr="")
    backend = WindowsSpeechBackend(executable="powershell.exe", platform_name="Windows", runner=runner)
    assert backend.capabilities().output_available
    assert not backend.capabilities().input_available


def test_missing_model_never_triggers_a_download(tmp_path):
    backend = VoskInput(tmp_path)
    with pytest.raises(VoiceUnavailableError, match="Modelo português ausente"):
        backend.prepare()


def test_amplify_pcm16_increases_quiet_audio_and_clips_peaks():
    source = array("h", [1_000, -1_000, 20_000, -20_000]).tobytes()
    amplified = array("h")
    amplified.frombytes(amplify_pcm16(source, 2.0))

    assert amplified.tolist() == [2_000, -2_000, 32_767, -32_768]


def fake_input(tmp_path, monkeypatch, *, confidence=0.99, overflow=False, accepted=True, transcripts=None):
    (tmp_path / "final.mdl").touch()
    phrases = ["que horas são"] if transcripts is None else transcripts
    results = iter(phrases)
    decisions = iter([accepted] * len(phrases) if isinstance(accepted, bool) else accepted)
    state = {"closed": False, "blocks": 0, "opened": 0}
    class Recognizer:
        def SetWords(self, enabled):
            assert enabled
        def AcceptWaveform(self, block):
            self.text = next(results)
            state["blocks"] += 1
            return next(decisions)
        def Result(self):
            return json.dumps({"text": self.text, "result": [{"conf": confidence}]})
    class Stream:
        def __init__(self, **kwargs):
            self.callback = kwargs["callback"]
        def __enter__(self):
            state["opened"] += 1
            for _ in phrases:
                self.callback(b"fake audio", 1, None, overflow)
            return self
        def __exit__(self, *args):
            state["closed"] = True
    vosk = SimpleNamespace(SetLogLevel=lambda value: None, Model=lambda path: object(), KaldiRecognizer=lambda model, rate: Recognizer())
    sd = SimpleNamespace(query_devices=lambda *args: {"default_samplerate": 16000, "name": "fake microphone"}, check_input_settings=lambda **kwargs: None, RawInputStream=Stream)
    backend = VoskInput(tmp_path)
    monkeypatch.setattr(backend, "_dependencies", lambda: (vosk, sd))
    return backend, state


def test_phonetic_detector_returns_only_canonical_huli(monkeypatch):
    state = {"words": [], "processed": [], "ended": False}

    class Decoder:
        def add_word(self, word, phones, update):
            state["words"].append((word, phones, update))

        def add_kws(self, name, path):
            state["kws"] = (name, path)

        def activate_search(self, name):
            state["search"] = name

        def start_utt(self):
            state["started"] = True

        def process_raw(self, block, no_search, full_utt):
            state["processed"].append(block)

        def hyp(self):
            return SimpleNamespace(hypstr="HULI RULI")

        def end_utt(self):
            state["ended"] = True

    decoder = Decoder()

    class Stream:
        def __init__(self, **kwargs):
            self.callback = kwargs["callback"]

        def __enter__(self):
            self.callback(b"\0\0" * 4_800, 4_800, None, False)
            return self

        def __exit__(self, *args):
            state["closed"] = True

    pocketsphinx = SimpleNamespace(Decoder=lambda **kwargs: decoder)
    sounddevice = SimpleNamespace(
        query_devices=lambda *args: {
            "default_samplerate": 48_000,
            "name": "fake microphone",
        },
        check_input_settings=lambda **kwargs: None,
        RawInputStream=Stream,
    )
    backend = PhoneticWakeInput()
    monkeypatch.setattr(
        backend,
        "_dependencies",
        lambda: (pocketsphinx, sounddevice),
    )

    assert backend.listen_once(timeout=2) == "huli"
    assert ("HULI", "HH UW L IY", False) in state["words"]
    assert ("RULI", "R UW L IY", False) in state["words"]
    assert len(state["processed"][0]) == 3_200
    assert state["ended"] is True
    assert state["closed"] is True


def test_final_recognition_closes_microphone(tmp_path, monkeypatch):
    backend, state = fake_input(tmp_path, monkeypatch)
    assert backend.listen_once(language="pt-BR", timeout=2) == "que horas são"
    assert state["closed"]


def test_wake_recognition_returns_isolated_name_without_waiting_for_command(tmp_path, monkeypatch):
    backend, state = fake_input(tmp_path, monkeypatch, transcripts=["olhe"])
    assert backend.listen_once(
        language="pt-BR",
        timeout=2,
        normalize_transcript=False,
    ) == "olhe"
    assert state["closed"]


@pytest.mark.parametrize("transcript", ["huli", "ruli", "ruly", "ru li"])
def test_medium_confidence_name_can_only_open_second_stage(tmp_path, monkeypatch, transcript):
    backend, state = fake_input(
        tmp_path,
        monkeypatch,
        confidence=0.50,
        transcripts=[transcript],
    )
    assert backend.listen_once(
        language="pt-BR",
        timeout=2,
        normalize_transcript=False,
    ) == transcript
    assert state["closed"]


def test_medium_confidence_calibrated_alias_can_only_open_wake_stage(tmp_path, monkeypatch):
    backend, state = fake_input(
        tmp_path,
        monkeypatch,
        confidence=0.50,
        transcripts=["ruly"],
    )
    assert backend.listen_once(
        language="pt-BR",
        timeout=2,
        normalize_transcript=False,
        wake_aliases=("ruly",),
    ) == "ruly"
    assert state["closed"]


def test_calibration_can_observe_low_confidence_text_but_does_not_execute_it(
    tmp_path,
    monkeypatch,
):
    backend, state = fake_input(
        tmp_path,
        monkeypatch,
        confidence=0.10,
        transcripts=["forma aproximada"],
    )
    assert backend.listen_once(
        language="pt-BR",
        timeout=2,
        normalize_transcript=False,
        calibration=True,
    ) == "forma aproximada"
    assert state["closed"]


def test_uncertain_recognition_is_not_an_executable_command(tmp_path, monkeypatch):
    backend, state = fake_input(tmp_path, monkeypatch, confidence=0.2)
    with pytest.raises(VoiceError, match="segurança"):
        backend.listen_once(language="pt-BR", timeout=2)
    assert state["closed"]


@pytest.mark.parametrize("transcript", ["hoje são", "que horas são"])
def test_medium_confidence_is_accepted_only_for_public_time_query(tmp_path, monkeypatch, transcript):
    backend, state = fake_input(
        tmp_path,
        monkeypatch,
        confidence=0.55,
        transcripts=[transcript],
    )
    recognized = backend.listen_once(language="pt-BR", timeout=2)
    assert IntentEngine().classify(recognized).intent == IntentName.TIME_QUERY
    assert state["closed"]


@pytest.mark.parametrize("transcript", [
    "apague a memória 1",
    "diário leia minhas entradas",
    "adicionar tarefa trocar filtro",
    "frase desconhecida",
])
def test_medium_confidence_still_rejects_private_writing_or_unknown_command(tmp_path, monkeypatch, transcript):
    backend, state = fake_input(
        tmp_path,
        monkeypatch,
        confidence=0.55,
        transcripts=[transcript],
    )
    with pytest.raises(VoiceError, match="segurança"):
        backend.listen_once(language="pt-BR", timeout=2)
    assert state["closed"]


def test_overflow_is_reported_and_microphone_closed(tmp_path, monkeypatch):
    backend, state = fake_input(tmp_path, monkeypatch, overflow=True)
    with pytest.raises(VoiceError, match="perda de áudio"):
        backend.listen_once(language="pt-BR", timeout=2)
    assert state["closed"]


def test_timeout_does_not_promote_partial_transcript(tmp_path, monkeypatch):
    backend, state = fake_input(tmp_path, monkeypatch, accepted=False)
    with pytest.raises(VoiceTimeoutError):
        backend.listen_once(language="pt-BR", timeout=0)
    assert state["closed"]


def test_missing_vosk_does_not_hide_tts(tmp_path, monkeypatch):
    backend = LocalVoiceBackend(model_path=tmp_path, input_provider="vosk")
    monkeypatch.setattr(backend.synthesis, "capabilities", lambda: SimpleNamespace(output_available=True, input_available=False, detail="pt-BR disponível"))
    result = backend.capabilities()
    assert result.output_available
    assert not result.input_available


@pytest.mark.parametrize(("transcript", "expected", "intent"), [
    ("huli que horas são", "que horas são", IntentName.TIME_QUERY),
    ("ruli que dia é hoje", "que dia é hoje", IntentName.DATE_QUERY),
    ("ru li que horas são", "que horas são", IntentName.TIME_QUERY),
    ("Huli, qual é a data de hoje?", "qual é a data de hoje?", IntentName.DATE_QUERY),
    ("hoje são", "que horas são", IntentName.TIME_QUERY),
    ("que hoje", "que dia é hoje", IntentName.DATE_QUERY),
    ("que horas são", "que horas são", IntentName.TIME_QUERY),
])
def test_spoken_name_before_time_or_date_reaches_correct_intent(tmp_path, monkeypatch, transcript, expected, intent):
    backend, state = fake_input(tmp_path, monkeypatch, transcripts=[transcript])
    recognized = backend.listen_once(language="pt-BR", timeout=2)
    assert recognized == expected
    assert IntentEngine().classify(recognized).intent == intent
    assert state["closed"]


@pytest.mark.parametrize(("phrases", "expected"), [
    (["huli", "que horas são"], "que horas são"),
    (["ruli", "", "que horas são"], "que horas são"),
    (["huli", "ruli", "que dia é hoje"], "que dia é hoje"),
])
def test_pause_after_name_keeps_same_stream_for_question(tmp_path, monkeypatch, phrases, expected):
    backend, state = fake_input(tmp_path, monkeypatch, transcripts=phrases)
    assert backend.listen_once(language="pt-BR", timeout=2) == expected
    assert state == {"closed": True, "blocks": len(phrases), "opened": 1}


@pytest.mark.parametrize(("phrases", "accepted", "ticks"), [
    (["huli"], True, [0, 1, 1, 11]),
    (["huli", "ruli"], True, [0, 1, 1, 9, 9, 11]),
    (["ruli", "que horas"], [True, False], [0, 1, 1, 9, 9, 11]),
])
def test_call_without_complete_question_expires_without_extending_deadline(tmp_path, monkeypatch, phrases, accepted, ticks):
    backend, state = fake_input(tmp_path, monkeypatch, transcripts=phrases, accepted=accepted)
    clock = iter(ticks)
    monkeypatch.setattr("huli.voice.local.time", SimpleNamespace(monotonic=lambda: next(clock)))
    with pytest.raises(VoiceTimeoutError, match="sem a pergunta completa"):
        backend.listen_once(language="pt-BR", timeout=10)
    assert state["closed"]
    assert state["blocks"] == len(phrases)
    assert not backend._listen_lock.locked()


@pytest.mark.parametrize("transcript", ["huli", "ruli que horas são", "hoje são"])
def test_vocative_correction_does_not_bypass_confidence_check(tmp_path, monkeypatch, transcript):
    backend, state = fake_input(tmp_path, monkeypatch, confidence=0.2, transcripts=[transcript])
    with pytest.raises(VoiceError, match="segurança"):
        backend.listen_once(language="pt-BR", timeout=2)
    assert state["closed"]


@pytest.mark.parametrize("text", [
    "olhe apague a memória 1",
    "olhe cancele o compromisso 1",
    "Huli apague a memória 1",
    "olhe que horas são e apague a memória 1",
    "olhe não pergunte que horas são",
    "olhe que horas são não",
    "diário: ela disse olhe que horas são",
    "lembre que olhe é uma palavra",
    "adicionar tarefa: olhe a piscina",
    "olheiro que horas são",
    "alguém disse olhe que horas são",
    "olha que horas são",
    "hoje são três pessoas",
    "não hoje são",
    "diário: hoje são lembranças importantes",
])
def test_other_transcripts_are_preserved_verbatim(text):
    assert normalize_spoken_vocative(text) == text


def test_real_name_can_precede_sensitive_intent_without_executing_it_here(tmp_path, monkeypatch):
    backend, _ = fake_input(tmp_path, monkeypatch, transcripts=["huli", "apague a memória 1"])
    recognized = backend.listen_once(language="pt-BR", timeout=2)
    assert recognized == "huli apague a memória 1"
    assert IntentEngine().classify(recognized).intent == IntentName.MEMORY_FORGET


def test_correction_does_not_change_typed_intents():
    assert IntentEngine().classify("olhe que horas são").intent == IntentName.UNKNOWN
    assert IntentEngine().classify("hoje são").intent == IntentName.UNKNOWN


@pytest.mark.parametrize("text", ["bom dia único", "boa tarde único", "boa noite único"])
def test_unrelated_words_are_not_rewritten_as_huli(text):
    assert normalize_spoken_vocative(text) == text


@pytest.mark.parametrize(("text", "expected"), [
    ("Huli!", True), ("Ruli", True), ("Ruly", True), ("Ru li", True),
    ("olhe", False), ("Juli", False), ("único", False),
    ("olheiro", False),
    ("olhe a janela", False), ("diário olhe", False), ("", False),
])
def test_only_isolated_vocative_waits_for_continuation(text, expected):
    assert is_spoken_vocative(text) is expected
