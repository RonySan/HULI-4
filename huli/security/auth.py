"""Autenticação local da fundação da Huli."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets

from huli.infrastructure.database import SQLiteDatabase
from huli.security.policy import SecurityPolicy


class AuthenticationError(ValueError):
    """Credenciais inválidas ou sessão não autorizada."""


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    id: int
    username: str


class AuthService:
    """Gerencia usuário proprietário e sessões opacas armazenadas por hash."""

    def __init__(self, database: SQLiteDatabase, policy: SecurityPolicy | None = None) -> None:
        self.database = database
        self.policy = policy or SecurityPolicy()

    def has_users(self) -> bool:
        with self.database.connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS total FROM users").fetchone()
            return bool(row and int(row["total"]) > 0)

    def find_user(self, username: str) -> AuthenticatedUser | None:
        """Retorna um usuário ativo pelo nome, sem autenticar sua sessão."""
        try:
            normalized = self._normalize_username(username)
        except ValueError:
            return None
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT id, username
                FROM users
                WHERE username = ? COLLATE NOCASE
                  AND is_active = 1
                """,
                (normalized,),
            ).fetchone()
        if row is None:
            return None
        return AuthenticatedUser(id=int(row["id"]), username=str(row["username"]))

    def requires_password(self, username: str) -> bool:
        """Indica se o usuário configurou uma senha não vazia."""
        normalized = self._normalize_username(username)
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT password_hash, password_salt, is_active
                FROM users
                WHERE username = ? COLLATE NOCASE
                """,
                (normalized,),
            ).fetchone()
        if row is None or not bool(row["is_active"]):
            raise AuthenticationError("Usuário não encontrado.")

        expected = bytes.fromhex(str(row["password_hash"]))
        salt = bytes.fromhex(str(row["password_salt"]))
        empty_password_hash = self._hash_password("", salt)
        return not hmac.compare_digest(expected, empty_password_hash)

    def create_owner(self, username: str, password: str = "") -> AuthenticatedUser:
        username = self._normalize_username(username)
        password = str(password or "").strip()
        self.policy.validate_password(password)
        salt = secrets.token_bytes(16)
        password_hash = self._hash_password(password, salt)

        with self.database.connect() as connection:
            try:
                cursor = connection.execute(
                    """
                    INSERT INTO users(username, password_hash, password_salt)
                    VALUES (?, ?, ?)
                    """,
                    (username, password_hash.hex(), salt.hex()),
                )
            except Exception as exc:
                if "UNIQUE" in str(exc).upper():
                    raise ValueError("Esse usuário já existe.") from exc
                raise
            return AuthenticatedUser(id=int(cursor.lastrowid), username=username)

    def set_password(self, username: str, new_password: str = "") -> None:
        """Altera ou remove a senha local de um usuário ativo."""
        normalized = self._normalize_username(username)
        password = str(new_password or "").strip()
        self.policy.validate_password(password)
        salt = secrets.token_bytes(16)
        password_hash = self._hash_password(password, salt)

        with self.database.connect() as connection:
            cursor = connection.execute(
                """
                UPDATE users
                SET password_hash = ?, password_salt = ?
                WHERE username = ? COLLATE NOCASE
                  AND is_active = 1
                """,
                (password_hash.hex(), salt.hex(), normalized),
            )
            if cursor.rowcount != 1:
                raise AuthenticationError("Usuário não encontrado.")
            connection.execute(
                """
                UPDATE sessions
                SET revoked_at = ?
                WHERE user_id = (
                    SELECT id FROM users WHERE username = ? COLLATE NOCASE
                )
                  AND revoked_at IS NULL
                """,
                (datetime.now(timezone.utc).isoformat(), normalized),
            )

    def authenticate(self, username: str, password: str = "") -> tuple[AuthenticatedUser, str]:
        username = self._normalize_username(username)
        password = str(password or "").strip()
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT id, username, password_hash, password_salt, is_active
                FROM users
                WHERE username = ? COLLATE NOCASE
                """,
                (username,),
            ).fetchone()

        if row is None or not bool(row["is_active"]):
            raise AuthenticationError("Usuário ou senha inválidos.")

        expected = bytes.fromhex(str(row["password_hash"]))
        salt = bytes.fromhex(str(row["password_salt"]))
        actual = self._hash_password(password, salt)
        if not hmac.compare_digest(expected, actual):
            raise AuthenticationError("Usuário ou senha inválidos.")

        user = AuthenticatedUser(id=int(row["id"]), username=str(row["username"]))
        token = secrets.token_urlsafe(32)
        self._store_session(user.id, token)
        return user, token

    def validate_token(self, token: str) -> AuthenticatedUser:
        if not token:
            raise AuthenticationError("Token ausente.")
        token_hash = self._hash_token(token)
        now = datetime.now(timezone.utc).isoformat()
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT u.id, u.username
                FROM sessions s
                JOIN users u ON u.id = s.user_id
                WHERE s.token_hash = ?
                  AND s.revoked_at IS NULL
                  AND s.expires_at > ?
                  AND u.is_active = 1
                """,
                (token_hash, now),
            ).fetchone()

        if row is None:
            raise AuthenticationError("Sessão inválida ou expirada.")
        return AuthenticatedUser(id=int(row["id"]), username=str(row["username"]))

    def revoke_token(self, token: str) -> None:
        if not token:
            return
        token_hash = self._hash_token(token)
        with self.database.connect() as connection:
            connection.execute(
                "UPDATE sessions SET revoked_at = ? WHERE token_hash = ? AND revoked_at IS NULL",
                (datetime.now(timezone.utc).isoformat(), token_hash),
            )

    def _store_session(self, user_id: int, token: str) -> None:
        created_at = datetime.now(timezone.utc)
        expires_at = created_at + timedelta(hours=self.policy.session_hours)
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO sessions(token_hash, user_id, created_at, expires_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    self._hash_token(token),
                    user_id,
                    created_at.isoformat(),
                    expires_at.isoformat(),
                ),
            )

    @staticmethod
    def _hash_password(password: str, salt: bytes) -> bytes:
        return hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=2**14,
            r=8,
            p=1,
            dklen=32,
        )

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def _normalize_username(username: str) -> str:
        normalized = str(username or "").strip()
        if len(normalized) < 3:
            raise ValueError("O usuário precisa ter pelo menos 3 caracteres.")
        if len(normalized) > 64:
            raise ValueError("O usuário pode ter no máximo 64 caracteres.")
        return normalized
