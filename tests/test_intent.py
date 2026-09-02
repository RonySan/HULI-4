"""Testes do Intent Engine local e determinístico."""

import pytest

from huli.brain import IntentEngine, IntentName, normalize_text


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("que horas são?", IntentName.TIME_QUERY),
        ("Qual é a hora?", IntentName.TIME_QUERY),
        ("qual o status da Huli?", IntentName.SYSTEM_STATUS),
        ("status huli", IntentName.SYSTEM_STATUS),
        ("o que temos pra fazer hoje?", IntentName.AGENDA_QUERY),
        ("minha agenda", IntentName.AGENDA_QUERY),
        ("temos compromissos para hoje", IntentName.AGENDA_QUERY),
        ("agenda para amanhã união com alto às oito horas da manhã", IntentName.AGENDA_CREATE),
        ("pode concluir compromisso e hoje", IntentName.AGENDA_COMPLETE),
        ("pode realizar esse compromisso de hoje", IntentName.AGENDA_COMPLETE),
        ("abrir o programa Google Chrome", IntentName.APP_OPEN),
        ("Huli, abra a calculadora", IntentName.APP_OPEN),
        ("adiciona uma tarefa revisar o Medynx", IntentName.TASK_CREATE),
        ("criar uma tarefa atualizar servidor", IntentName.TASK_CREATE),
        ("oi Huli", IntentName.SMALL_TALK),
        ("oi huli, bom dia", IntentName.SMALL_TALK),
        ("bom dia", IntentName.MORNING_BRIEFING),
        ("Huli, bom dia", IntentName.MORNING_BRIEFING),
        ("como você está huli?", IntentName.SMALL_TALK),
        ("boa noite", IntentName.SMALL_TALK),
        ("qual o status do projeto Medynx?", IntentName.PROJECT_QUERY),
        ("como está o projeto Huli?", IntentName.PROJECT_QUERY),
    ],
)
def test_classifies_fundamental_intents(text: str, expected: IntentName) -> None:
    result = IntentEngine().classify(text)

    assert result.intent is expected
    assert result.confidence >= 0.95
    assert result.metadata["matched_rule"] != "none"


def test_normalization_removes_accents_case_and_punctuation() -> None:
    assert normalize_text("  QUAL É A HÓRA?!  ") == "qual e a hora"


def test_unknown_is_controlled_and_does_not_guess() -> None:
    result = IntentEngine().classify("comprar tinta azul para a garagem")

    assert result.intent is IntentName.UNKNOWN
    assert result.confidence == 0.0
    assert result.metadata["matched_rule"] == "none"


@pytest.mark.parametrize("text", ("abrir o link", "abrir o site", "abrir arquivo relatório"))
def test_opening_non_app_content_is_not_treated_as_an_application(text: str) -> None:
    assert IntentEngine().classify(text).intent is IntentName.UNKNOWN


def test_heat_exchanger_does_not_trigger_time_or_other_false_positive() -> None:
    result = IntentEngine().classify("trocar o trocador de calor da piscina")

    assert result.intent is IntentName.UNKNOWN


def test_empty_text_is_unknown_instead_of_inventing_intent() -> None:
    result = IntentEngine().classify("   ")

    assert result.intent is IntentName.UNKNOWN
    assert result.metadata["matched_rule"] == "empty"
