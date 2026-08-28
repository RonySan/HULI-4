"""Intenções específicas da Fase 4."""

from huli.brain import IntentEngine, IntentName


def test_conversation_mode_set_intents() -> None:
    engine = IntentEngine()

    assert engine.classify("modo profissional").intent is IntentName.CONVERSATION_MODE_SET
    assert engine.classify("ative modo casual").intent is IntentName.CONVERSATION_MODE_SET
    assert engine.classify("modo sério").intent is IntentName.CONVERSATION_MODE_SET
    assert engine.classify("modo automático").intent is IntentName.CONVERSATION_MODE_SET


def test_conversation_mode_query_intent() -> None:
    engine = IntentEngine()

    assert engine.classify("qual o modo atual").intent is IntentName.CONVERSATION_MODE_QUERY


def test_identity_questions_are_smalltalk() -> None:
    engine = IntentEngine()

    assert engine.classify("quem é você?").intent is IntentName.SMALL_TALK
    assert engine.classify("o que significa Huli?").intent is IntentName.SMALL_TALK
    assert engine.classify("o que você consegue fazer?").intent is IntentName.SMALL_TALK
