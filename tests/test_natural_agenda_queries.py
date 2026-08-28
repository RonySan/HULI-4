"""Regressões para consultas naturais da Agenda."""

from pathlib import Path

import pytest

from huli.bootstrap import build_runtime
from huli.brain import IntentEngine, IntentName
from huli.infrastructure import Settings


@pytest.mark.parametrize(
    "text",
    [
        "agenda",
        "agendas",
        "minha agenda",
        "o que temos na agenda",
        "o que eu tenho na agenda?",
        "o que tem na agenda?",
        "tem algo na agenda?",
        "quais meus compromissos?",
        "mostrar agenda",
        "consultar minha agenda",
        "Huli, o que temos na agenda?",
    ],
)
def test_natural_agenda_queries_map_to_agenda_query(text: str) -> None:
    result = IntentEngine().classify(text)

    assert result.intent is IntentName.AGENDA_QUERY
    assert result.confidence >= 0.95


def test_user_reported_agenda_queries_reach_agenda_skill(tmp_path: Path) -> None:
    runtime = build_runtime(
        Settings(environment="test", log_level="CRITICAL", data_dir=tmp_path)
    )
    metadata = {
        "session_id": "agenda-natural",
        "username": "rony",
        "role": "owner",
    }

    for text in ("agendas", "o que temos na agenda"):
        response = runtime.kernel.process(text, metadata=metadata)
        assert response.handled_by == "agenda"
        assert response.ok is True
        assert "compromissos" in response.text.casefold()
