"""Regressões da verificação executada antes dos inicializadores."""

from pathlib import Path

import huli_preflight


def test_preflight_explains_missing_core_dependency(monkeypatch) -> None:
    available = huli_preflight._module_available
    monkeypatch.setattr(
        huli_preflight,
        "_module_available",
        lambda name: False if name == "cryptography" else available(name),
    )

    report = huli_preflight.inspect_installation()

    assert not report.ok
    assert "cryptography" in huli_preflight.format_report(report)
    assert "pip install -e ." in huli_preflight.format_report(report)


def test_voice_preflight_accepts_complete_local_whisper(
    tmp_path: Path,
    monkeypatch,
) -> None:
    for filename in ("model.bin", "config.json", "tokenizer.json"):
        (tmp_path / filename).touch()
    monkeypatch.setenv("HULI_VOICE_WHISPER_MODEL_PATH", str(tmp_path))
    available = huli_preflight._module_available
    monkeypatch.setattr(
        huli_preflight,
        "_module_available",
        lambda name: True
        if name in {"sounddevice", "pocketsphinx", "faster_whisper"}
        else available(name),
    )

    report = huli_preflight.inspect_installation(include_voice=True)

    assert report.ok
    assert not report.warnings
    assert "voz local verificadas" in huli_preflight.format_report(
        report,
        include_voice=True,
    )
