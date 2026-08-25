"""Testes de autenticação e política de segurança."""

from pathlib import Path

import pytest

from huli.infrastructure import SQLiteDatabase
from huli.security import AuthenticationError, AuthService, SecurityPolicy


def build_auth(tmp_path: Path) -> AuthService:
    database = SQLiteDatabase(tmp_path / "huli.db")
    database.initialize()
    return AuthService(database, SecurityPolicy(session_hours=1))


def test_owner_authentication_round_trip(tmp_path: Path) -> None:
    auth = build_auth(tmp_path)
    owner = auth.create_owner("rony", "senha-segura-123")

    user, token = auth.authenticate("rony", "senha-segura-123")

    assert user.id == owner.id
    assert user.username == "rony"
    assert auth.requires_password("rony") is True
    assert auth.validate_token(token).id == owner.id

    auth.revoke_token(token)
    with pytest.raises(AuthenticationError):
        auth.validate_token(token)


def test_owner_can_be_created_without_password(tmp_path: Path) -> None:
    auth = build_auth(tmp_path)
    owner = auth.create_owner("rony")

    assert auth.find_user("rony") == owner
    assert auth.requires_password("rony") is False

    user, token = auth.authenticate("rony")
    assert user == owner
    assert auth.validate_token(token) == owner


def test_authentication_rejects_wrong_password(tmp_path: Path) -> None:
    auth = build_auth(tmp_path)
    auth.create_owner("rony", "senha-segura-123")

    with pytest.raises(AuthenticationError):
        auth.authenticate("rony", "senha-errada")


def test_unknown_user_is_not_treated_as_owner(tmp_path: Path) -> None:
    auth = build_auth(tmp_path)
    auth.create_owner("rony")

    assert auth.find_user("visitante") is None
    with pytest.raises(AuthenticationError):
        auth.authenticate("visitante")


def test_security_policy_accepts_empty_password() -> None:
    SecurityPolicy().validate_password("")


def test_security_policy_rejects_too_short_non_empty_password() -> None:
    policy = SecurityPolicy(min_password_length=4)

    with pytest.raises(ValueError, match="opcional"):
        policy.validate_password("123")


def test_guest_policy_allows_only_basic_foundation_commands() -> None:
    policy = SecurityPolicy()

    assert policy.guest_can_execute("ping") is True
    assert policy.guest_can_execute("status huli") is True
    assert policy.guest_can_execute("abrir calculadora") is False
    assert policy.guest_can_execute("mostrar minhas memórias") is False
