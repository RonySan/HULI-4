"""Regressões reproduzidas a partir do uso real por voz."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from huli.bootstrap import build_runtime
from huli.infrastructure import Settings


def test_month_agenda_query_lists_this_month(tmp_path: Path) -> None:
    runtime = build_runtime(Settings(environment="test", log_level="CRITICAL", data_dir=tmp_path))
    now = runtime.agenda.now()
    appointment = runtime.agenda.create("teste mensal", now + timedelta(minutes=10))
    metadata = {"session_id": "month", "username": "Rony", "role": "owner"}

    response = runtime.kernel.process(
        "você sabe quando tem compromissos esse mês",
        metadata=metadata,
    )

    assert response.handled_by == "agenda"
    assert "Compromissos deste mês" in response.text
    assert f"#{appointment.id}" in response.text
    assert "teste mensal" in response.text


def test_plural_habit_phrase_creates_clean_name(tmp_path: Path) -> None:
    runtime = build_runtime(Settings(environment="test", log_level="CRITICAL", data_dir=tmp_path))
    metadata = {"session_id": "habit-voice", "username": "Rony", "role": "owner"}

    response = runtime.kernel.process("criar hábitos para beber água", metadata=metadata)

    assert response.handled_by == "habits"
    assert response.ok is True
    assert runtime.habit_repository.list_active("Rony")[0].name == "beber água"


def test_spoken_compound_spotify_command_routes_to_favorites(tmp_path: Path) -> None:
    runtime = build_runtime(Settings(environment="test", log_level="CRITICAL", data_dir=tmp_path))
    called = []
    runtime.media.play_favorites = lambda: called.append("favorites")  # type: ignore[method-assign]
    metadata = {"session_id": "media-voice", "username": "Rony", "role": "owner"}

    response = runtime.kernel.process(
        "abrir esportes pai e tocar as minhas favoritas",
        metadata=metadata,
    )

    assert response.handled_by == "media"
    assert response.ok is True
    assert called == ["favorites"]
