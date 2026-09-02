"""Calibração da palavra de ativação sem microfone ou áudio real."""

import json

from huli.voice.calibration import (
    WakeAliasStore,
    normalize_wake_alias,
    select_repeated_aliases,
)
from huli.voice.wake import extract_wake_command


def test_only_repeated_short_name_forms_are_selected() -> None:
    samples = ["Rúli", "ruli", "ru li", "Ru Li", "hoje"]

    assert select_repeated_aliases(samples) == ("ru li", "ruli")


def test_wrong_vosk_spellings_never_become_the_name() -> None:
    samples = ["o link", "rubi", "ruim", "único"]

    assert select_repeated_aliases(samples * 2) == ()


def test_one_or_two_ambiguous_words_do_not_create_an_alias() -> None:
    assert select_repeated_aliases(["ruim", "rubi"]) == ()


def test_common_commands_and_long_phrases_cannot_become_wake_aliases() -> None:
    assert normalize_wake_alias("hoje") is None
    assert normalize_wake_alias("boa tarde") is None
    assert normalize_wake_alias("que horas são agora") is None
    assert select_repeated_aliases(["agenda", "agenda", "voz", "voz"]) == ()


def test_alias_store_persists_only_selected_text_not_samples(tmp_path) -> None:
    path = tmp_path / "voice_wake_aliases.json"
    store = WakeAliasStore(path)

    assert store.save(("Rúli", "ru li")) == ("ruli", "ru li")
    assert store.load() == ("ruli", "ru li")
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert set(payload) == {"version", "aliases", "updated_at"}
    assert "audio" not in path.read_text(encoding="utf-8").casefold()


def test_corrupt_or_unsafe_alias_file_fails_closed(tmp_path) -> None:
    path = tmp_path / "voice_wake_aliases.json"
    path.write_text('{"aliases": ["hoje", "ruli", "ruli"]}', encoding="utf-8")
    assert WakeAliasStore(path).load() == ("ruli",)
    path.write_text("não é json", encoding="utf-8")
    assert WakeAliasStore(path).load() == ()


def test_calibrated_alias_only_matches_at_start_and_preserves_command() -> None:
    aliases = ("ruly",)

    assert extract_wake_command("ruly que horas são", aliases) == "que horas são"
    assert extract_wake_command("ruly", aliases) == ""
    assert extract_wake_command("não chame ruly", aliases) is None
