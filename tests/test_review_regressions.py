"""Regressões reproduzidas na revisão de 31/08; somente bancos fictícios."""

from datetime import datetime
import json
from zoneinfo import ZoneInfo

import pytest

import main as cli
from huli.bootstrap import build_runtime
from huli.infrastructure import Settings, load_settings
from huli.infrastructure.config import APP_ROOT
from huli.security import AuthenticationError


@pytest.fixture
def runtime(tmp_path):
    return build_runtime(
        Settings(
            environment="test",
            log_level="CRITICAL",
            data_dir=tmp_path,
            local_login_enabled=True,
        )
    )


def meta():
    return {"username": "review_user", "role": "owner", "session_id": "review"}


@pytest.mark.parametrize("phrase", ["lembre que minha senha e {}", "adicionar tarefa usar token {}", "diário: minha senha e {}", "o projeto usa api-key {}"])
def test_secrets_never_reach_events_context_or_persistence(runtime, phrase):
    marker = "SEGREDO_FICTICIO_7319"
    observed = []
    runtime.events.subscribe("kernel.request.received", lambda event: observed.append(event.payload))
    runtime.events.subscribe("brain.intent.classified", lambda event: observed.append(event.payload))
    response = runtime.kernel.process(phrase.format(marker), metadata=meta())
    assert not response.ok
    assert response.handled_by == "privacy"
    assert runtime.memory_repository.count_active("review_user") == 0
    assert not runtime.planner.pending()
    assert marker not in json.dumps(observed)
    assert not any(marker in turn.text for turn in runtime.context.recent_turns("review"))
    with runtime.database.connect() as connection:
        assert not connection.execute("SELECT 1 FROM events WHERE payload_json LIKE ?", (f"%{marker}%",)).fetchone()
        assert not connection.execute("SELECT 1 FROM interactions WHERE user_text LIKE ? OR response_text LIKE ?", (f"%{marker}%", f"%{marker}%")).fetchone()


def test_cli_rejects_revoked_expired_and_forged_sessions(runtime):
    runtime.auth.create_owner("review_user")
    user, token = runtime.auth.authenticate("review_user")
    session = cli.CliSession(user.username, "owner", token)
    assert cli._can_execute(runtime, session, "minhas memorias")
    assert not cli._can_execute(runtime, cli.CliSession("another", "owner", token), "minhas memorias")
    runtime.auth.revoke_token(token)
    with pytest.raises(AuthenticationError):
        runtime.auth.validate_token(token)
    assert not cli._can_execute(runtime, session, "minhas memorias")
    _, fresh_token = runtime.auth.authenticate("review_user")
    with runtime.database.connect() as connection:
        connection.execute("UPDATE sessions SET expires_at = '2000-01-01T00:00:00+00:00'")
    assert not cli._can_execute(runtime, cli.CliSession(user.username, "owner", fresh_token), "minhas memorias")


def test_old_memory_remains_searchable_after_200_new_entries(runtime):
    old = runtime.memory.remember(owner="review_user", content="xilofonetestevioleta")
    for index in range(205):
        runtime.memory.remember(owner="review_user", content=f"anotacao recente {index}")
    runtime.memory.remember(owner="another", content="xilofonetestevioleta")
    matches = runtime.memory.recall(owner="review_user", query=old.content)
    assert [item.id for item in matches] == [old.id]
    assert runtime.memory.forget(owner="review_user", target=old.content).id == old.id


@pytest.mark.parametrize(("period", "expected"), [("de manhã", {"MANHA"}), ("à tarde", {"TARDE", "FIM_TARDE"}), ("à noite", {"NOITE"}), ("à noite?", {"NOITE"})])
def test_agenda_filters_periods_including_boundaries(runtime, period, expected):
    tz = ZoneInfo("America/Sao_Paulo")
    runtime.agenda.now = lambda: datetime(2026, 8, 31, 12, tzinfo=tz)
    names = {"MANHA": (9, 0), "TARDE": (12, 0), "FIM_TARDE": (17, 59), "NOITE": (18, 0)}
    for name, (hour, minute) in names.items():
        runtime.agenda.create(name, datetime(2026, 8, 31, hour, minute, tzinfo=tz))
    response = runtime.kernel.process(f"verifique minha agenda para hoje {period} huli", metadata=meta())
    assert response.ok
    for line in response.text.splitlines()[1:]:
        if "—" in line:
            assert line.split("— ")[1] in expected
    assert sum("—" in line for line in response.text.splitlines()) == len(expected)


def test_natural_task_completion_and_ambiguity(runtime):
    runtime.kernel.process("adicionar tarefa verificar trocador de calor da piscina", metadata=meta())
    response = runtime.kernel.process("trocador de calor verificado", metadata=meta())
    assert response.ok and "concluída" in response.text
    assert not runtime.planner.pending()
    runtime.planner.create_task("verificar bomba piscina")
    runtime.planner.create_task("verificar bomba garagem")
    ambiguous = runtime.kernel.process("bomba verificada", metadata=meta())
    assert not ambiguous.ok and "mais de uma" in ambiguous.text
    assert len(runtime.planner.pending()) == 2
    for phrase in ("bomba não verificada", "bomba verificada?"):
        assert runtime.intents.classify(phrase).intent.value == "unknown"


@pytest.mark.parametrize("phrase", ["como vai huli", "o que temos pra hoje a tarde huli", "verifique minah agenda par ahoje a tarde huli"])
def test_user_phrases_are_understood(runtime, phrase):
    assert runtime.intents.classify(phrase).intent.value != "unknown"


def test_data_location_does_not_depend_on_working_directory(tmp_path, monkeypatch):
    before = load_settings({}).database_path
    monkeypatch.chdir(tmp_path)
    assert load_settings({}).database_path == before == APP_ROOT / "data" / "huli.db"
    assert load_settings({"HULI_DATA_DIR": "another-data"}).data_dir == APP_ROOT / "another-data"
    assert load_settings({"HULI_DATA_DIR": str(tmp_path)}).data_dir == tmp_path
