"""Testes da personalidade e continuidade conversacional da Huli."""

from pathlib import Path

from huli.bootstrap import build_runtime
from huli.core import Event
from huli.infrastructure import Settings
from huli.personality import ConversationMode


def build_test_runtime(tmp_path: Path):
    return build_runtime(
        Settings(
            environment="test",
            log_level="CRITICAL",
            data_dir=tmp_path,
            timezone="America/Sao_Paulo",
        )
    )


def test_personality_resolves_modes_deterministically(tmp_path: Path) -> None:
    runtime = build_test_runtime(tmp_path)

    casual = runtime.personality.decide(text="oi huli", intent="smalltalk")
    professional = runtime.personality.decide(
        text="minhas tarefas",
        intent="task.list",
    )
    serious = runtime.personality.decide(
        text="temos uma falha crítica urgente",
        intent="unknown",
    )
    risk = runtime.personality.decide(
        text="esqueça 1",
        intent="memory.forget",
    )

    assert casual.mode is ConversationMode.CASUAL
    assert professional.mode is ConversationMode.PROFESSIONAL
    assert serious.mode is ConversationMode.SERIOUS
    assert risk.mode is ConversationMode.RISK


def test_social_followup_is_resolved_from_short_context(tmp_path: Path) -> None:
    runtime = build_test_runtime(tmp_path)
    meta = {"session_id": "social", "username": "rony", "role": "owner"}

    first = runtime.kernel.process("oi huli", metadata=meta)
    followup = runtime.kernel.process("e você?", metadata=meta)

    assert first.handled_by == "smalltalk"
    assert followup.handled_by == "smalltalk"
    assert "operacional" in followup.text.casefold()
    assert runtime.context.snapshot("social").last_intent == "smalltalk"


def test_identity_expands_acronym_only_when_asked(tmp_path: Path) -> None:
    runtime = build_test_runtime(tmp_path)
    meta = {"session_id": "identity", "username": "rony", "role": "owner"}

    greeting = runtime.kernel.process("oi huli", metadata=meta)
    meaning = runtime.kernel.process("o que significa Huli?", metadata=meta)

    assert "Humano Único Leal Inteligente" not in greeting.text
    assert meaning.handled_by == "smalltalk"
    assert "Humano Único Leal Inteligente" in meaning.text
    assert "meu nome é Huli" in meaning.text


def test_active_project_switches_smalltalk_to_professional_mode(tmp_path: Path) -> None:
    runtime = build_test_runtime(tmp_path)
    meta = {"session_id": "work", "username": "rony", "role": "owner"}
    decisions: list[Event] = []
    runtime.events.subscribe("conversation.mode.selected", decisions.append)

    runtime.kernel.process("vamos falar do projeto Medynx", metadata=meta)
    response = runtime.kernel.process("como você está huli?", metadata=meta)

    assert response.handled_by == "smalltalk"
    assert "seguir com o trabalho" in response.text.casefold()
    assert decisions[-1].payload["mode"] == "professional"


def test_personality_does_not_rewrite_memory_facts(tmp_path: Path) -> None:
    runtime = build_test_runtime(tmp_path)
    meta = {"session_id": "facts", "username": "rony", "role": "owner"}

    runtime.kernel.process(
        "lembre que eu prefiro relatórios objetivos",
        metadata=meta,
    )
    recalled = runtime.kernel.process(
        "o que você lembra sobre relatórios?",
        metadata=meta,
    )

    assert recalled.handled_by == "memory"
    assert "relatórios objetivos" in recalled.text
    assert recalled.text.startswith("Encontrei")
