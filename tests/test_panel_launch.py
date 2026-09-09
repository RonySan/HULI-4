"""Testes das opções usadas pelos atalhos do painel."""

import os

import painel


def test_resident_launch_enables_wake_and_spoken_answers(monkeypatch) -> None:
    for key in (
        "HULI_DESKTOP_RESIDENT_ENABLED",
        "HULI_VOICE_WAKE_ENABLED",
        "HULI_VOICE_AUTO_SPEAK",
    ):
        monkeypatch.delenv(key, raising=False)

    painel.apply_launch_options(["--resident"])

    assert os.environ["HULI_DESKTOP_RESIDENT_ENABLED"] == "true"
    assert os.environ["HULI_VOICE_WAKE_ENABLED"] == "true"
    assert os.environ["HULI_VOICE_AUTO_SPEAK"] == "true"


def test_minimized_launch_hides_panel_after_start(monkeypatch) -> None:
    monkeypatch.delenv("HULI_DESKTOP_START_MINIMIZED", raising=False)

    painel.apply_launch_options(["--minimized"])

    assert os.environ["HULI_DESKTOP_START_MINIMIZED"] == "true"
