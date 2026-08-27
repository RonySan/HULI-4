"""Integração do diário com linguagem natural, privacidade e API."""

from datetime import timedelta
import json
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from huli.api import create_app
from huli.bootstrap import build_runtime
from huli.brain import IntentEngine, IntentName
from huli.infrastructure import Settings
from huli.personality import ConversationMode
from huli.security import PRIVATE_JOURNAL_REDACTION


def build_test_runtime(tmp_path: Path):
    runtime = build_runtime(
        Settings(
            environment="test",
            log_level="CRITICAL",
            data_dir=tmp_path,
            timezone="America/Sao_Paulo",
        )
    )
    runtime.auth.create_owner("rony", "1234")
    return runtime


def owner_metadata(session_id: str = "journal") -> dict[str, str]:
    return {"session_id": session_id, "username": "rony", "role": "owner"}


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("diário: hoje consegui concluir uma etapa importante", IntentName.JOURNAL_CREATE),
        ("anote no meu diário: passei a tarde com minha família", IntentName.JOURNAL_CREATE),
        ("meu diário de hoje", IntentName.JOURNAL_LIST),
        ("o que escrevi ontem no diário?", IntentName.JOURNAL_LIST),
        ("procure no meu diário por família", IntentName.JOURNAL_SEARCH),
        ("edite a entrada #1 do diário: texto corrigido", IntentName.JOURNAL_UPDATE),
        ("apague a entrada #1 do diário", IntentName.JOURNAL_DELETE),
        ("lixeira do meu diário", IntentName.JOURNAL_TRASH),
        ("restaure a entrada #1 do diário", IntentName.JOURNAL_RESTORE),
        ("como uso meu diário?", IntentName.JOURNAL_HELP),
    ],
)
def test_journal_intents_are_deterministic(text: str, expected: IntentName) -> None:
    assert IntentEngine().classify(text).intent is expected


def test_owner_can_write_list_search_edit_and_delete_journal(
    tmp_path: Path,
) -> None:
    runtime = build_test_runtime(tmp_path)
    meta = owner_metadata()

    created = runtime.kernel.process(
        "diário: hoje finalizei a evolução da Huli | humor: feliz | "
        "tags: trabalho, Huli",
        metadata=meta,
    )
    listed = runtime.kernel.process("meu diário de hoje", metadata=meta)
    searched = runtime.kernel.process(
        "procure no meu diário por evolução",
        metadata=meta,
    )
    edited = runtime.kernel.process(
        "edite a entrada #1 do diário: hoje finalizei e testei a evolução da Huli",
        metadata=meta,
    )
    after_edit = runtime.kernel.process(
        "procure no meu diário por testei",
        metadata=meta,
    )
    deleted = runtime.kernel.process(
        "apague a entrada #1 do diário",
        metadata=meta,
    )
    trash = runtime.kernel.process("lixeira do meu diário", metadata=meta)
    restored = runtime.kernel.process(
        "restaure a entrada #1 do diário",
        metadata=meta,
    )

    assert created.handled_by == "journal" and created.ok
    assert "Entrada #1 salva" in created.text
    assert "humor: feliz" in listed.text
    assert "etiquetas: trabalho, huli" in listed.text
    assert "evolução da Huli" in searched.text
    assert edited.handled_by == "journal" and edited.ok
    assert "finalizei e testei" in after_edit.text
    assert deleted.handled_by == "journal" and deleted.ok
    assert "finalizei e testei" in trash.text
    assert restored.handled_by == "journal" and restored.ok
    assert runtime.journal_repository.count_active("rony") == 1


def test_journal_supports_yesterday_and_persists_without_becoming_memory(
    tmp_path: Path,
) -> None:
    runtime = build_test_runtime(tmp_path)
    meta = owner_metadata("journal-yesterday")

    created = runtime.kernel.process(
        "anote no meu diário de ontem: visitei um lugar muito especial",
        metadata=meta,
    )
    yesterday = runtime.journal.today() - timedelta(days=1)
    entries = runtime.journal.entries_on(owner="rony", entry_date=yesterday)

    assert created.ok
    assert len(entries) == 1
    assert entries[0].content == "visitei um lugar muito especial"
    assert runtime.memory_repository.count_active("rony") == 0
    assert runtime.knowledge_repository.list_entities("rony") == ()


def test_guest_and_unidentified_requests_cannot_access_journal(tmp_path: Path) -> None:
    runtime = build_test_runtime(tmp_path)
    guest = {"session_id": "guest", "username": "Visitante", "role": "guest"}

    denied_write = runtime.kernel.process(
        "diário: esta entrada nunca deve ser salva",
        metadata=guest,
    )
    denied_read = runtime.kernel.process("meu diário", metadata=guest)
    denied_trash = runtime.kernel.process("lixeira do meu diário", metadata=guest)
    unidentified = runtime.kernel.process(
        "diário: também não deve ser salva",
        metadata={"session_id": "missing-role", "username": "rony"},
    )

    assert not denied_write.ok and "proprietário" in denied_write.text
    assert not denied_read.ok and "proprietário" in denied_read.text
    assert not denied_trash.ok and "proprietário" in denied_trash.text
    assert not unidentified.ok
    assert runtime.journal_repository.count_active("rony") == 0


def test_passwordless_owner_must_protect_account_before_using_journal(
    tmp_path: Path,
) -> None:
    runtime = build_runtime(
        Settings(environment="test", log_level="CRITICAL", data_dir=tmp_path)
    )
    runtime.auth.create_owner("rony")
    meta = owner_metadata("journal-passwordless")

    denied = runtime.kernel.process(
        "diário: esta entrada exige uma conta protegida",
        metadata=meta,
    )
    help_response = runtime.kernel.process("como uso meu diário?", metadata=meta)

    assert not denied.ok
    assert "configure uma senha" in denied.text
    assert help_response.ok
    assert runtime.journal_repository.count_active("rony") == 0


def test_journal_content_is_redacted_from_events_interactions_and_context(
    tmp_path: Path,
) -> None:
    runtime = build_test_runtime(tmp_path)
    private_sentence = "hoje pensei em uma surpresa muito pessoal"
    meta = owner_metadata("journal-private")

    response = runtime.kernel.process(
        f"diário: {private_sentence}",
        metadata=meta,
    )
    assert response.ok

    latest = runtime.interactions.latest(1)[0]
    assert latest.user_text == PRIVATE_JOURNAL_REDACTION
    assert latest.response_text == PRIVATE_JOURNAL_REDACTION
    assert runtime.context.recent_turns("journal-private")[0].text == PRIVATE_JOURNAL_REDACTION

    with runtime.database.connect() as connection:
        payloads = [
            json.loads(str(row["payload_json"]))
            for row in connection.execute("SELECT payload_json FROM events").fetchall()
        ]
    serialized = json.dumps(payloads, ensure_ascii=False)
    assert private_sentence not in serialized
    assert PRIVATE_JOURNAL_REDACTION in serialized

    recap = runtime.kernel.process(
        "o que conversamos mais cedo?",
        metadata=meta,
    )
    assert not recap.ok
    assert private_sentence not in recap.text


def test_unrecognized_diary_phrase_fails_private_without_becoming_project_memory(
    tmp_path: Path,
) -> None:
    runtime = build_test_runtime(tmp_path)
    meta = owner_metadata("journal-fallback")
    runtime.kernel.process("vamos falar do projeto Medynx", metadata=meta)

    response = runtime.kernel.process(
        "no meu diário pessoal o Medynx teve um dia diferente",
        metadata=meta,
    )

    assert response.handled_by == "journal"
    assert response.ok
    assert "Exemplos" in response.text
    assert runtime.memory_repository.count_active("rony") == 0
    assert runtime.context.recent_turns("journal-fallback")[-1].text == PRIVATE_JOURNAL_REDACTION


def test_journal_uses_private_personality_mode_and_delete_uses_risk(
    tmp_path: Path,
) -> None:
    runtime = build_test_runtime(tmp_path)

    private = runtime.personality.decide(
        text="meu diário de hoje",
        intent="journal.list",
    )
    risk = runtime.personality.decide(
        text="apague a entrada #1 do diário",
        intent="journal.delete",
    )

    assert private.mode is ConversationMode.PRIVATE
    assert risk.mode is ConversationMode.RISK


def test_authenticated_api_uses_the_same_private_journal(tmp_path: Path) -> None:
    runtime = build_test_runtime(tmp_path)
    client = TestClient(create_app(runtime))
    login = client.post(
        "/v1/auth/login",
        json={"username": "rony", "password": "1234"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    saved = client.post(
        "/v1/messages",
        headers=headers,
        json={"text": "diário: escrevi pelo aplicativo", "session_id": "journal-api"},
    )
    listed = client.post(
        "/v1/messages",
        headers=headers,
        json={"text": "meu diário de hoje", "session_id": "journal-api"},
    )

    assert saved.status_code == 200
    assert saved.json()["handled_by"] == "journal"
    assert listed.status_code == 200
    assert "escrevi pelo aplicativo" in listed.json()["text"]
