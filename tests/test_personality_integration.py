"""Integração da personalidade com Kernel, Skills e API."""

from pathlib import Path

from fastapi.testclient import TestClient

from huli.api import create_app
from huli.bootstrap import build_runtime
from huli.infrastructure import Settings


def _runtime(tmp_path: Path):
    return build_runtime(
        Settings(environment="test", log_level="CRITICAL", data_dir=tmp_path)
    )


def test_manual_professional_mode_changes_smalltalk_without_changing_facts(
    tmp_path: Path,
) -> None:
    runtime = _runtime(tmp_path)
    meta = {"session_id": "p1", "username": "rony", "role": "owner"}

    mode = runtime.kernel.process("modo profissional", metadata=meta)
    greeting = runtime.kernel.process("oi Huli", metadata=meta)
    saved = runtime.kernel.process(
        "lembre que eu prefiro café sem açúcar",
        metadata=meta,
    )
    recalled = runtime.kernel.process(
        "o que você lembra sobre café?",
        metadata=meta,
    )

    assert mode.handled_by == "conversation-mode"
    assert runtime.conversation.snapshot("p1").mode.value == "professional"
    assert "objetiva" in greeting.text or "projetos" in greeting.text
    assert saved.handled_by == "memory"
    assert "café sem açúcar" in recalled.text


def test_frustrated_unknown_request_gets_serious_non_fake_fallback(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    meta = {"session_id": "p2", "username": "rony", "role": "owner"}

    response = runtime.kernel.process(
        "não está funcionando, deu errado de novo",
        metadata=meta,
    )
    snapshot = runtime.conversation.snapshot("p2")

    assert response.handled_by == "brain-dispatcher"
    assert response.ok is False
    assert "não está funcionando" in response.text
    assert "não vou fingir" in response.text
    assert snapshot.mode.value == "serious"
    assert snapshot.humor_allowed is False


def test_risk_request_disables_humor_but_does_not_remove_manual_mode(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    meta = {"session_id": "p3", "username": "rony", "role": "owner"}

    runtime.kernel.process("modo casual", metadata=meta)
    risky = runtime.kernel.process("apagar tudo agora", metadata=meta)
    risk_snapshot = runtime.conversation.snapshot("p3")
    runtime.kernel.process("oi Huli", metadata=meta)
    after = runtime.conversation.snapshot("p3")

    assert risky.ok is False
    assert "sensível" in risky.text
    assert risk_snapshot.mode.value == "risk"
    assert risk_snapshot.humor_allowed is False
    assert after.mode.value == "casual"
    assert after.override is not None


def test_identity_expands_acronym_only_when_asked(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    meta = {"session_id": "p4", "username": "rony", "role": "owner"}

    normal = runtime.kernel.process("quem é você?", metadata=meta)
    meaning = runtime.kernel.process("o que significa Huli?", metadata=meta)

    assert "Sou a Huli" in normal.text
    assert "Humano Único Leal Inteligente" not in normal.text
    assert "Humano Único Leal Inteligente" in meaning.text


def test_api_preserves_conversation_mode_by_session(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    runtime.auth.create_owner("rony", "1234")
    client = TestClient(create_app(runtime))
    login = client.post(
        "/v1/auth/login",
        json={"username": "rony", "password": "1234"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    set_mode = client.post(
        "/v1/messages",
        headers=headers,
        json={"text": "modo profissional", "session_id": "mobile-p4"},
    )
    greeting = client.post(
        "/v1/messages",
        headers=headers,
        json={"text": "oi Huli", "session_id": "mobile-p4"},
    )
    other_session = client.post(
        "/v1/messages",
        headers=headers,
        json={"text": "oi Huli", "session_id": "mobile-other"},
    )

    assert set_mode.status_code == 200
    assert set_mode.json()["conversation_mode"] == "professional"
    assert greeting.json()["conversation_mode"] == "professional"
    assert greeting.json()["humor_allowed"] is True
    assert other_session.json()["conversation_mode"] == "casual"
