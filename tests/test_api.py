"""Testes da API autenticada da Huli."""

from pathlib import Path

from fastapi.testclient import TestClient

from huli.api import create_app
from huli.bootstrap import build_runtime
from huli.infrastructure import Settings


def build_client(tmp_path: Path) -> tuple[TestClient, object]:
    runtime = build_runtime(
        Settings(environment="test", log_level="CRITICAL", data_dir=tmp_path)
    )
    return TestClient(create_app(runtime)), runtime


def test_health_is_public(tmp_path: Path) -> None:
    client, _runtime = build_client(tmp_path)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["schema_version"] == 7


def test_messages_require_authentication(tmp_path: Path) -> None:
    client, _runtime = build_client(tmp_path)

    response = client.post("/v1/messages", json={"text": "ping"})

    assert response.status_code == 401


def test_passwordless_owner_can_login_with_empty_password(tmp_path: Path) -> None:
    client, _runtime = build_client(tmp_path)

    setup = client.post("/v1/auth/setup", json={"username": "rony"})
    assert setup.status_code == 201
    assert setup.json()["password_protected"] is False

    login = client.post("/v1/auth/login", json={"username": "rony"})
    assert login.status_code == 200
    token = login.json()["access_token"]

    me = client.get("/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["username"] == "rony"


def test_full_authenticated_flow_and_persistence(tmp_path: Path) -> None:
    client, runtime = build_client(tmp_path)

    setup = client.post(
        "/v1/auth/setup",
        json={"username": "rony", "password": "senha-segura-123"},
    )
    assert setup.status_code == 201
    assert setup.json()["password_protected"] is True

    second_setup = client.post(
        "/v1/auth/setup",
        json={"username": "outro", "password": "senha-segura-456"},
    )
    assert second_setup.status_code == 409

    login = client.post(
        "/v1/auth/login",
        json={"username": "rony", "password": "senha-segura-123"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    me = client.get("/v1/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["username"] == "rony"

    message = client.post("/v1/messages", headers=headers, json={"text": "ping"})
    assert message.status_code == 200
    assert message.json()["handled_by"] == "foundation"
    assert message.json()["ok"] is True

    latest = runtime.interactions.latest(1)
    assert latest[0].user_text == "ping"
    assert latest[0].handled_by == "foundation"

    logout = client.post("/v1/auth/logout", headers=headers)
    assert logout.status_code == 204

    after_logout = client.get("/v1/me", headers=headers)
    assert after_logout.status_code == 401
