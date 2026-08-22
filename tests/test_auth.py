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
    assert auth.validate_token(token).id == owner.id

    auth.revoke_token(token)
    with pytest.raises(AuthenticationError):
        auth.validate_token(token)


def test_authentication_rejects_wrong_password(tmp_path: Path) -> None:
    auth = build_auth(tmp_path)
    auth.create_owner("rony", "senha-segura-123")

    with pytest.raises(AuthenticationError):
        auth.authenticate("rony", "senha-errada")


def test_security_policy_rejects_short_password() -> None:
    policy = SecurityPolicy(min_password_length=10)

    with pytest.raises(ValueError, match="pelo menos 10"):
        policy.validate_password("curta")
