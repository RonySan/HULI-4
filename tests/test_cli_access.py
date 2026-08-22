"""Testes do controle de acesso da interface local."""

from pathlib import Path

import main as cli

from huli.bootstrap import build_runtime
from huli.infrastructure import Settings


def build_test_runtime(tmp_path: Path):
    return build_runtime(
        Settings(environment="test", log_level="CRITICAL", data_dir=tmp_path)
    )


def test_first_run_can_create_owner_without_password(tmp_path: Path, monkeypatch) -> None:
    runtime = build_test_runtime(tmp_path)
    answers = iter(["rony", "rony"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(answers))
    monkeypatch.setattr(cli, "getpass", lambda _prompt="": "")

    session = cli._authenticate(runtime)

    assert session.role == "owner"
    assert session.username == "rony"
    assert session.token
    assert runtime.auth.requires_password("rony") is False


def test_unknown_username_enters_guest_mode(tmp_path: Path, monkeypatch) -> None:
    runtime = build_test_runtime(tmp_path)
    runtime.auth.create_owner("rony")
    monkeypatch.setattr("builtins.input", lambda _prompt="": "joao")

    session = cli._authenticate(runtime)

    assert session.role == "guest"
    assert session.username == "joao"
    assert session.token is None


def test_guest_is_limited_to_safe_foundation_commands(tmp_path: Path) -> None:
    runtime = build_test_runtime(tmp_path)
    guest = cli.CliSession(username="Visitante", role="guest")
    owner = cli.CliSession(username="rony", role="owner", token="token")

    assert cli._can_execute(runtime, guest, "ping") is True
    assert cli._can_execute(runtime, guest, "abrir calculadora") is False
    assert cli._can_execute(runtime, owner, "abrir calculadora") is True
