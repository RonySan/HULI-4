"""Regressões das frases reais usadas por Rony na validação da Huli."""

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from huli.bootstrap import build_runtime
from huli.brain import IntentEngine, IntentName
from huli.infrastructure import Settings
from huli.skills.parsing import parse_appointment_request


def build_test_runtime(tmp_path: Path):
    return build_runtime(
        Settings(
            environment="test",
            log_level="CRITICAL",
            data_dir=tmp_path,
            timezone="America/Sao_Paulo",
        )
    )


def owner_metadata(session_id: str = "natural-language") -> dict[str, str]:
    return {
        "session_id": session_id,
        "username": "rony",
        "role": "owner",
    }


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("que dia é hoje?", IntentName.DATE_QUERY),
        ("como está a agenda pra hoje?", IntentName.AGENDA_QUERY),
        ("como está nossa agenda essa noite?", IntentName.AGENDA_QUERY),
        ("agenda", IntentName.AGENDA_QUERY),
        ("temos compromissos hoje à noite?", IntentName.AGENDA_QUERY),
        (
            "agenda pra mim jantar às 22 horas com a Gisele",
            IntentName.AGENDA_CREATE,
        ),
        ("o que conversamos mais cedo?", IntentName.CONVERSATION_RECAP),
        (
            "ok, então vamos começar os trabalhos de hoje",
            IntentName.SMALL_TALK,
        ),
    ],
)
def test_real_user_phrasings_have_stable_intents(
    text: str,
    expected: IntentName,
) -> None:
    assert IntentEngine().classify(text).intent is expected


def test_date_agenda_and_work_start_are_handled(tmp_path: Path) -> None:
    runtime = build_test_runtime(tmp_path)
    meta = owner_metadata()

    work = runtime.kernel.process(
        "ok, então vamos começar os trabalhos de hoje",
        metadata=meta,
    )
    date = runtime.kernel.process("que dia é hoje?", metadata=meta)
    today = runtime.kernel.process("como está a agenda pra hoje?", metadata=meta)
    tonight = runtime.kernel.process(
        "como está nossa agenda essa noite?",
        metadata=meta,
    )
    short = runtime.kernel.process("agenda", metadata=meta)

    assert work.handled_by == "smalltalk"
    assert "primeira prioridade" in work.text.casefold()
    assert date.handled_by == "time"
    assert date.text.startswith("Hoje é ")
    assert today.handled_by == "agenda"
    assert "hoje" in today.text.casefold()
    assert tonight.handled_by == "agenda"
    assert "noite" in tonight.text.casefold()
    assert short.handled_by == "agenda"


def test_appointment_without_date_uses_next_safe_occurrence() -> None:
    timezone = ZoneInfo("America/Sao_Paulo")
    evening = datetime(2026, 8, 26, 18, 0, tzinfo=timezone)

    title, same_day = parse_appointment_request(
        "agenda pra mim jantar às 22 horas com a Gisele",
        timezone_name="America/Sao_Paulo",
        now=evening,
    )
    _title, next_day = parse_appointment_request(
        "agenda jantar às 17 horas com a Gisele",
        timezone_name="America/Sao_Paulo",
        now=evening,
    )

    assert title == "jantar com a Gisele"
    assert same_day.isoformat() == "2026-08-26T22:00:00-03:00"
    assert next_day.isoformat() == "2026-08-27T17:00:00-03:00"


def test_natural_project_update_becomes_memory_task_and_knowledge(
    tmp_path: Path,
) -> None:
    runtime = build_test_runtime(tmp_path)
    meta = owner_metadata("project-note")
    runtime.kernel.process("vamos falar do projeto Medynx", metadata=meta)

    response = runtime.kernel.process(
        "o Medynx é um novo projeto desenvolvido para clínicas, "
        "depois precisamos rever os logins dos pacientes que estão com problema",
        metadata=meta,
    )
    memories = runtime.memory_repository.list_active("rony")
    tasks = runtime.tasks.list_pending(project="Medynx")
    knowledge = runtime.kernel.process(
        "o que você sabe sobre Medynx?",
        metadata=meta,
    )
    recap = runtime.kernel.process("o que conversamos mais cedo?", metadata=meta)

    assert response.handled_by == "project-context"
    assert response.ok
    assert len(memories) == 1
    assert memories[0].project == "Medynx"
    assert memories[0].source.value == "automatic"
    assert "precisamos" not in memories[0].content.casefold()
    assert len(tasks) == 1
    assert tasks[0].title == "rever os logins dos pacientes que estão com problema"
    assert knowledge.handled_by == "knowledge"
    assert "descrição:" in knowledge.text
    assert "novo projeto desenvolvido para clínicas" in knowledge.text
    assert recap.handled_by == "conversation"
    assert "Medynx" in recap.text
    assert "projeto ativo continua" in recap.text.casefold()


def test_masculine_priority_word_is_normalized_and_removed_from_title(
    tmp_path: Path,
) -> None:
    runtime = build_test_runtime(tmp_path)
    meta = owner_metadata("priority")
    runtime.kernel.process("vamos falar do projeto Medynx", metadata=meta)

    response = runtime.kernel.process(
        "adiciona uma tarefa revisar o banco prioridade alto",
        metadata=meta,
    )
    task = runtime.tasks.list_pending(project="Medynx")[0]

    assert response.handled_by == "planner"
    assert "prioridade alta" in response.text
    assert task.priority == "alta"
    assert task.title == "revisar o banco"


def test_tasks_appointments_and_memory_survive_runtime_restart(
    tmp_path: Path,
) -> None:
    settings = Settings(
        environment="test",
        log_level="CRITICAL",
        data_dir=tmp_path,
        timezone="America/Sao_Paulo",
    )
    first = build_runtime(settings)
    meta = owner_metadata("persistence-first")
    first.kernel.process("adiciona uma tarefa revisar o banco", metadata=meta)
    first.kernel.process("agenda jantar amanhã às 22:00", metadata=meta)
    first.kernel.process("lembre que o Medynx usa MySQL", metadata=meta)

    second = build_runtime(settings)

    assert second.tasks.list_pending()[0].title == "revisar o banco"
    assert second.agenda.upcoming(limit=10)[0].title == "jantar"
    assert second.memory.recall(owner="rony", query="Medynx MySQL")


def test_guest_can_read_date_but_not_private_conversation(tmp_path: Path) -> None:
    runtime = build_test_runtime(tmp_path)

    assert runtime.security.guest_can_execute("que dia é hoje?", "date.query")
    assert not runtime.security.guest_can_execute(
        "o que conversamos mais cedo?",
        "conversation.recap",
    )


def test_automatic_project_note_cannot_store_a_secret(tmp_path: Path) -> None:
    runtime = build_test_runtime(tmp_path)
    meta = owner_metadata("project-secret")
    runtime.kernel.process("vamos falar do projeto Medynx", metadata=meta)

    response = runtime.kernel.process(
        "o Medynx tem a senha secreta123",
        metadata=meta,
    )

    assert response.handled_by == "project-context"
    assert not response.ok
    assert "não armazena senhas" in response.text.casefold()
    assert runtime.memory_repository.count_active("rony") == 0


def test_conversation_recap_is_isolated_by_session(tmp_path: Path) -> None:
    runtime = build_test_runtime(tmp_path)
    runtime.kernel.process(
        "adiciona uma tarefa revisar o banco",
        metadata=owner_metadata("session-a"),
    )

    other_session = runtime.kernel.process(
        "o que conversamos mais cedo?",
        metadata=owner_metadata("session-b"),
    )

    assert other_session.handled_by == "conversation"
    assert not other_session.ok
    assert "não há uma conversa anterior nesta sessão" in other_session.text.casefold()
