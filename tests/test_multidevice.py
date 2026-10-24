"""Contrato de segurança e disponibilidade do cliente web multidispositivo."""

from pathlib import Path

from fastapi.testclient import TestClient

from huli.api import create_app
from huli.bootstrap import build_runtime
from huli.infrastructure import Settings


def make_client(tmp_path: Path, remote: bool = False):
    runtime = build_runtime(
        Settings(
            environment="test",
            log_level="CRITICAL",
            data_dir=tmp_path,
            remote_access_enabled=remote,
        )
    )
    return TestClient(create_app(runtime)), runtime


def test_web_client_is_served_without_exposing_data(tmp_path: Path):
    client, _runtime = make_client(tmp_path)
    html = client.get("/app")
    assert html.status_code == 200
    assert "Bem-vindo à Huli" in html.text
    assert "no-store" in html.headers["cache-control"]
    assert "script-src 'self'" in html.headers["content-security-policy"]
    assert "frame-ancestors 'none'" in html.headers["content-security-policy"]
    assert client.get("/app/static/app.js").status_code == 200
    assert client.get("/app/static/style.css").status_code == 200
    assert client.get("/app/static/manifest.webmanifest").status_code == 200


def test_private_mode_disables_remote_setup_and_weak_login(tmp_path: Path):
    client, runtime = make_client(tmp_path, remote=True)
    runtime.auth.create_owner("rony", "senha-bem-segura")
    assert client.post("/v1/auth/setup", json={"username": "outro", "password": "nova-senha-123"}).status_code == 403
    assert client.post("/v1/auth/login", json={"username": "rony", "password": ""}).status_code == 403
    assert client.post("/v1/auth/login", json={"username": "rony", "password": "1234"}).status_code == 403
    response = client.post("/v1/auth/login", json={"username": "rony", "password": "senha-bem-segura"})
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["access_token"]


def test_private_mode_blocks_pc_and_journal_actions(tmp_path: Path):
    client, runtime = make_client(tmp_path, remote=True)
    runtime.auth.create_owner("rony", "senha-bem-segura")
    response = client.post("/v1/auth/login", json={"username": "rony", "password": "senha-bem-segura"})
    headers = {"Authorization": "Bearer " + response.json()["access_token"]}
    for text in ("abrir o Google Chrome", "diário: conteúdo particular", "esqueça minha memória"):
        denied = client.post("/v1/messages", headers=headers, json={"text": text})
        assert denied.status_code == 403, (text, denied.text)
    allowed = client.post("/v1/messages", headers=headers, json={"text": "ping"})
    assert allowed.status_code == 200
    assert allowed.json()["ok"] is True


def test_private_mode_rate_limits_failed_logins(tmp_path: Path):
    client, runtime = make_client(tmp_path, remote=True)
    runtime.auth.create_owner("rony", "senha-bem-segura")
    for _ in range(6):
        response = client.post("/v1/auth/login", json={"username": "rony", "password": "senha-incorreta"})
        assert response.status_code == 401
    blocked = client.post("/v1/auth/login", json={"username": "rony", "password": "senha-bem-segura"})
    assert blocked.status_code == 429


def test_local_mode_retains_existing_passwordless_api(tmp_path: Path):
    client, _runtime = make_client(tmp_path, remote=False)
    assert client.post("/v1/auth/setup", json={"username": "rony"}).status_code == 201
    assert client.post("/v1/auth/login", json={"username": "rony"}).status_code == 200


def test_remote_policy_checks_effective_intent_after_personality(tmp_path: Path, monkeypatch):
    from types import SimpleNamespace

    client, runtime = make_client(tmp_path, remote=True)
    runtime.auth.create_owner("rony", "senha-bem-segura")
    login = client.post("/v1/auth/login", json={"username": "rony", "password": "senha-bem-segura"})
    headers = {"Authorization": "Bearer " + login.json()["access_token"]}

    real_decide = runtime.personality.decide

    def remap_unknown(**kwargs):
        if kwargs["intent"] == "unknown":
            return SimpleNamespace(
                intent="app.open",
                mode=SimpleNamespace(value="professional"),
                reason="test",
                is_followup=False,
            )
        return real_decide(**kwargs)

    monkeypatch.setattr(runtime.personality, "decide", remap_unknown)
    response = client.post("/v1/messages", headers=headers, json={"text": "palavras nao reconhecidas xyzxyz"})
    assert response.status_code == 403
    assert "apenas no computador local" in response.json()["detail"]
