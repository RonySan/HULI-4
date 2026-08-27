from pathlib import Path

from fastapi.testclient import TestClient

from huli.api import create_app
from huli.bootstrap import build_runtime
from huli.infrastructure import Settings


def build_test_runtime(tmp_path: Path):
    return build_runtime(
        Settings(environment="test", log_level="CRITICAL", data_dir=tmp_path)
    )


def test_kernel_can_remember_recall_list_and_forget(tmp_path: Path) -> None:
    runtime = build_test_runtime(tmp_path)
    meta = {"session_id": "memory-test", "username": "rony", "role": "owner"}

    saved = runtime.kernel.process(
        "lembre que eu prefiro café sem açúcar",
        metadata=meta,
    )
    recalled = runtime.kernel.process(
        "o que você lembra sobre café?",
        metadata=meta,
    )
    listed = runtime.kernel.process("minhas memórias", metadata=meta)

    assert saved.handled_by == "memory"
    assert "Memória #" in saved.text
    assert recalled.handled_by == "memory"
    assert "café sem açúcar" in recalled.text
    assert "café sem açúcar" in listed.text

    memory_id = runtime.memory_repository.list_active("rony")[0].id
    forgotten = runtime.kernel.process(
        f"esqueça {memory_id}",
        metadata=meta,
    )
    after = runtime.kernel.process(
        "o que você lembra sobre café?",
        metadata=meta,
    )

    assert "esquecida" in forgotten.text
    assert "Não encontrei" in after.text


def test_project_context_is_attached_to_new_memory(tmp_path: Path) -> None:
    runtime = build_test_runtime(tmp_path)
    meta = {"session_id": "project-memory", "username": "rony", "role": "owner"}

    runtime.kernel.process("vamos falar do projeto Medynx", metadata=meta)
    runtime.kernel.process(
        "lembre que a publicação depende de revisar o banco",
        metadata=meta,
    )

    memories = runtime.memory_repository.list_active("rony")
    assert memories[0].project == "Medynx"
    assert memories[0].kind.value == "project"


def test_guest_policy_does_not_allow_memory_intents(tmp_path: Path) -> None:
    runtime = build_test_runtime(tmp_path)

    assert runtime.security.guest_can_execute(
        "o que você lembra sobre café?",
        "memory.recall",
    ) is False
    assert runtime.security.guest_can_execute(
        "lembre que eu gosto de café",
        "memory.remember",
    ) is False


def test_memory_candidate_event_applies_policy(tmp_path: Path) -> None:
    runtime = build_test_runtime(tmp_path)

    runtime.events.publish(
        "memory.candidate",
        {
            "owner": "rony",
            "content": "prefiro interface escura",
            "kind": "preference",
            "confidence": 0.96,
        },
    )
    assert runtime.memory_repository.count_active("rony") == 1

    runtime.events.publish(
        "memory.candidate",
        {
            "owner": "rony",
            "content": "minha senha é exemplo123",
            "kind": "semantic",
            "confidence": 1.0,
        },
    )
    assert runtime.memory_repository.count_active("rony") == 1


def test_api_uses_the_same_persistent_memory_engine(tmp_path: Path) -> None:
    runtime = build_test_runtime(tmp_path)
    runtime.auth.create_owner("rony", "senha-1234")
    client = TestClient(create_app(runtime))

    login = client.post(
        "/v1/auth/login",
        json={"username": "rony", "password": "senha-1234"},
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    saved = client.post(
        "/v1/messages",
        headers=headers,
        json={
            "text": "lembre que eu prefiro café sem açúcar",
            "session_id": "mobile-memory",
        },
    )
    recalled = client.post(
        "/v1/messages",
        headers=headers,
        json={
            "text": "o que você lembra sobre café?",
            "session_id": "mobile-memory",
        },
    )

    assert saved.status_code == 200
    assert saved.json()["handled_by"] == "memory"
    assert recalled.status_code == 200
    assert "café sem açúcar" in recalled.json()["text"]
