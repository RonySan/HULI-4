"""Testes do controle de acesso da interface local."""

from pathlib import Path

import pytest

import main as cli

from huli.bootstrap import build_runtime
from huli.infrastructure import Settings


def build_test_runtime(tmp_path: Path):
    return build_runtime(
        Settings(
            environment="test",
            log_level="CRITICAL",
            data_dir=tmp_path,
            local_login_enabled=True,
        )
    )


def test_direct_main_uses_the_project_virtual_environment(monkeypatch) -> None:
    expected = Path(cli.__file__).resolve().parent / ".venv" / "Scripts" / "python.exe"
    executed = {}
    monkeypatch.setattr(cli.sys, "executable", r"C:\Python313\python.exe")
    monkeypatch.setattr(cli.sys, "argv", [str(Path(cli.__file__).resolve()), "--example"])
    monkeypatch.setattr(
        cli.subprocess,
        "run",
        lambda arguments, check: executed.update(arguments=arguments, check=check)
        or cli.subprocess.CompletedProcess(arguments, 7),
    )

    with pytest.raises(SystemExit) as stopped:
        cli._restart_with_project_python()

    assert stopped.value.code == 7
    assert executed == {
        "arguments": [str(expected), str(Path(cli.__file__).resolve()), "--example"],
        "check": False,
    }


def test_wake_queries_are_immediate_but_writes_require_keyboard_confirmation() -> None:
    for intent in (
        "time.query",
        "date.query",
        "agenda.query",
        "task.list",
        "project.query",
        "memory.recall",
        "smalltalk",
    ):
        assert not cli._wake_requires_confirmation(intent)
    for intent in (
        "agenda.create",
        "agenda.cancel",
        "task.create",
        "task.complete",
        "project.set",
        "project.note",
        "memory.remember",
        "memory.forget",
        "journal.create",
        "journal.list",
        "journal.delete",
    ):
        assert cli._wake_requires_confirmation(intent)


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


def test_local_owner_mode_skips_credentials_without_deleting_auth(tmp_path: Path) -> None:
    runtime = build_runtime(
        Settings(
            environment="test",
            log_level="CRITICAL",
            data_dir=tmp_path,
            local_login_enabled=False,
            local_owner_name="Rony",
        )
    )

    session = cli._authenticate(runtime)

    assert session.username == "Rony"
    assert session.role == "owner"
    assert session.token is None
    assert cli._can_execute(runtime, session, "listar minhas memórias")
    assert not runtime.auth.has_users()


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
    runtime.auth.create_owner("rony")
    _, token = runtime.auth.authenticate("rony")
    owner = cli.CliSession(username="rony", role="owner", token=token)

    assert cli._can_execute(runtime, guest, "ping") is True
    assert cli._can_execute(runtime, guest, "abrir calculadora") is False
    assert cli._can_execute(runtime, owner, "abrir calculadora") is True
