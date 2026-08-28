"""Testes do motor de personalidade e conversação."""

from huli.brain import ConversationEngine, ConversationMode, ConversationSignal


def test_smalltalk_defaults_to_casual() -> None:
    engine = ConversationEngine()

    snapshot = engine.analyze("s1", "oi Huli", "smalltalk")

    assert snapshot.mode is ConversationMode.CASUAL
    assert snapshot.signal is ConversationSignal.NEUTRAL
    assert snapshot.humor_allowed is True


def test_professional_intent_selects_professional_mode() -> None:
    engine = ConversationEngine()

    snapshot = engine.analyze("s1", "qual o status do projeto Medynx?", "project.query")

    assert snapshot.mode is ConversationMode.PROFESSIONAL
    assert snapshot.humor_allowed is True


def test_frustration_selects_serious_mode_and_disables_humor() -> None:
    engine = ConversationEngine()

    snapshot = engine.analyze("s1", "não está funcionando, deu errado", "unknown")

    assert snapshot.mode is ConversationMode.SERIOUS
    assert snapshot.signal is ConversationSignal.FRUSTRATION
    assert snapshot.humor_allowed is False


def test_risk_overrides_manual_casual_mode_temporarily() -> None:
    engine = ConversationEngine()
    engine.set_mode("s1", "casual")

    risky = engine.analyze("s1", "apagar tudo agora", "unknown")
    after = engine.analyze("s1", "oi Huli", "smalltalk")

    assert risky.mode is ConversationMode.RISK
    assert risky.humor_allowed is False
    assert after.mode is ConversationMode.CASUAL
    assert after.override is ConversationMode.CASUAL


def test_manual_professional_mode_persists_until_auto() -> None:
    engine = ConversationEngine()
    engine.set_mode("s1", "profissional")

    casual_input = engine.analyze("s1", "oi Huli", "smalltalk")
    automatic = engine.set_mode("s1", "automatico")
    after_auto = engine.analyze("s1", "oi Huli", "smalltalk")

    assert casual_input.mode is ConversationMode.PROFESSIONAL
    assert casual_input.override is ConversationMode.PROFESSIONAL
    assert automatic.override is None
    assert after_auto.mode is ConversationMode.CASUAL


def test_clear_removes_session_state() -> None:
    engine = ConversationEngine()
    engine.set_mode("s1", "serio")
    engine.analyze("s1", "teste", "unknown")

    engine.clear("s1")
    snapshot = engine.snapshot("s1")

    assert snapshot.mode is ConversationMode.CASUAL
    assert snapshot.override is None
    assert snapshot.turn_count == 0
