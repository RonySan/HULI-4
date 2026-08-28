"""Integração ponta a ponta do Knowledge Graph."""

from pathlib import Path

from fastapi.testclient import TestClient

from huli.api import create_app
from huli.bootstrap import build_runtime
from huli.infrastructure import Settings


def test_kernel_memory_to_knowledge_query(tmp_path: Path) -> None:
    runtime = build_runtime(
        Settings(environment="test", log_level="CRITICAL", data_dir=tmp_path)
    )
    meta = {"session_id": "knowledge", "username": "rony", "role": "owner"}

    saved = runtime.kernel.process(
        "lembre que Medynx é desenvolvido pela Impulso Digital",
        metadata=meta,
    )
    answered = runtime.kernel.process("quem desenvolve Medynx?", metadata=meta)
    described = runtime.kernel.process("o que você sabe sobre Medynx?", metadata=meta)

    assert saved.handled_by == "memory"
    assert answered.handled_by == "knowledge"
    assert "Impulso Digital" in answered.text
    assert described.handled_by == "knowledge"
    assert "desenvolvido por: Impulso Digital" in described.text


def test_unknown_knowledge_never_fabricates_answer(tmp_path: Path) -> None:
    runtime = build_runtime(
        Settings(environment="test", log_level="CRITICAL", data_dir=tmp_path)
    )
    meta = {"session_id": "knowledge", "username": "rony", "role": "owner"}

    response = runtime.kernel.process("quem desenvolve Projeto Fantasma?", metadata=meta)

    assert response.handled_by == "knowledge"
    assert response.ok is False
    assert "Não encontrei" in response.text


def test_api_uses_same_knowledge_graph(tmp_path: Path) -> None:
    runtime = build_runtime(
        Settings(environment="test", log_level="CRITICAL", data_dir=tmp_path)
    )
    runtime.auth.create_owner("rony", "1234")
    client = TestClient(create_app(runtime))
    login = client.post(
        "/v1/auth/login",
        json={"username": "rony", "password": "1234"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    saved = client.post(
        "/v1/messages",
        headers=headers,
        json={
            "text": "lembre que Medynx está hospedado no servidor Casa",
            "session_id": "knowledge-api",
        },
    )
    queried = client.post(
        "/v1/messages",
        headers=headers,
        json={
            "text": "qual servidor hospeda Medynx?",
            "session_id": "knowledge-api",
        },
    )

    assert saved.status_code == 200
    assert saved.json()["handled_by"] == "memory"
    assert queried.status_code == 200
    assert queried.json()["handled_by"] == "knowledge"
    assert "servidor Casa" in queried.json()["text"]


def test_guest_policy_does_not_allow_personal_knowledge(tmp_path: Path) -> None:
    runtime = build_runtime(
        Settings(environment="test", log_level="CRITICAL", data_dir=tmp_path)
    )

    assert not runtime.security.guest_can_execute(
        "quem desenvolve Medynx?",
        "knowledge.relation",
    )
