"""Cofre de chaves e criptografia em repouso do diário pessoal."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import hmac
from pathlib import Path
import re
import secrets
import sqlite3
import time
from typing import Callable, Protocol
from uuid import uuid4

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from huli.infrastructure.database import SQLiteDatabase
from huli.security.encrypted_file import seal_json, write_envelope
from huli.security.os_protection import (
    OSKeyProtector,
    OSProtectionError,
    PasswordOnlyProtector,
    default_os_key_protector,
)

_CRYPTO_VERSION = 1
_KDF_N = 2**14
_KDF_R = 8
_KDF_P = 1
_KEY_BYTES = 32
_NONCE_BYTES = 12


class VaultUser(Protocol):
    id: int
    username: str


class JournalVaultError(RuntimeError):
    """Falha segura do cofre privado."""


class JournalVaultLockedError(JournalVaultError):
    """O proprietário precisa autenticar novamente para abrir o diário."""


class JournalVaultIntegrityError(JournalVaultError):
    """Dado cifrado foi alterado, corrompido ou aberto com outra chave."""


@dataclass(frozen=True, slots=True)
class EncryptedValue:
    nonce: bytes
    ciphertext: bytes


@dataclass(frozen=True, slots=True)
class VaultUnlockResult:
    migrated_entries: int = 0
    migration_backup: Path | None = None
    os_protection: str = "password-only"


@dataclass(slots=True)
class _UnlockedKey:
    user_id: int
    owner: str
    key: bytearray
    last_used: float


class JournalVault:
    """Mantém somente chaves abertas em memória e as expira por inatividade."""

    def __init__(
        self,
        database: SQLiteDatabase,
        *,
        inactivity_minutes: int = 15,
        protector: OSKeyProtector | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.database = database
        self.inactivity_seconds = max(1, int(inactivity_minutes)) * 60
        self.protector = protector or default_os_key_protector()
        self._clock = clock
        self._unlocked: dict[str, _UnlockedKey] = {}
        self._last_results: dict[str, VaultUnlockResult] = {}

    @staticmethod
    def _owner_key(owner: str) -> str:
        return " ".join(str(owner or "").split()).strip().casefold()

    def has_vault(
        self,
        owner: str,
        *,
        connection: sqlite3.Connection | None = None,
    ) -> bool:
        if connection is not None:
            row = connection.execute(
                """
                SELECT 1
                FROM journal_vaults v
                JOIN users u ON u.id = v.user_id
                WHERE u.username = ? COLLATE NOCASE
                """,
                (owner,),
            ).fetchone()
            return row is not None
        with self.database.connect() as managed:
            return self.has_vault(owner, connection=managed)

    def is_unlocked(self, owner: str) -> bool:
        try:
            self._key_for(owner, touch=False)
        except JournalVaultLockedError:
            return False
        return True

    def unlock(self, user: VaultUser, password: str) -> VaultUnlockResult:
        password = str(password or "").strip()
        if not password:
            self.lock(user.username)
            raise JournalVaultLockedError(
                "O cofre do diário exige uma senha não vazia para ser aberto."
            )

        with self.database.connect() as connection:
            row = self._vault_row(connection, user.id)
            if row is None:
                master_key = secrets.token_bytes(_KEY_BYTES)
                self._insert_vault(connection, user, password, master_key)
            else:
                master_key = self._unwrap_master_key(row, user, password)
                if str(row["os_protection"]) != self.protector.name:
                    self._update_wrapped_key(
                        connection,
                        user,
                        password=password,
                        master_key=master_key,
                    )

        self._cache_key(user, master_key)
        try:
            migrated, backup_path = self._migrate_legacy_entries(user, password)
            self._complete_legacy_scrub(user)
        except Exception:
            self.lock(user.username)
            raise
        result = VaultUnlockResult(
            migrated_entries=migrated,
            migration_backup=backup_path,
            os_protection=self.protector.name,
        )
        self._last_results[self._owner_key(user.username)] = result
        return result

    def last_unlock_result(self, owner: str) -> VaultUnlockResult | None:
        return self._last_results.get(self._owner_key(owner))

    def prepare_password_change(
        self,
        user: VaultUser,
        new_password: str,
        *,
        connection: sqlite3.Connection,
    ) -> None:
        """Atualiza o envelope da chave na mesma transação da senha de login."""

        password = str(new_password or "").strip()
        row = self._vault_row(connection, user.id)
        if row is not None and not password:
            count_row = connection.execute(
                """
                SELECT COUNT(*) AS total
                FROM journal_entries
                WHERE owner = ? COLLATE NOCASE
                """,
                (user.username,),
            ).fetchone()
            if count_row and int(count_row["total"]) > 0:
                raise JournalVaultError(
                    "A senha não pode ser removida enquanto o diário possuir entradas. "
                    "Crie um backup criptografado antes de qualquer recuperação administrativa."
                )
            connection.execute(
                "DELETE FROM journal_vaults WHERE user_id = ?",
                (user.id,),
            )
            self.lock(user.username)
            return
        if row is None and not password:
            return

        if row is None:
            master_key = secrets.token_bytes(_KEY_BYTES)
            self._insert_vault(connection, user, password, master_key)
            self._cache_key(user, master_key)
            return

        master_key = bytes(self._key_for(user.username, touch=False))
        self._update_wrapped_key(
            connection,
            user,
            password=password,
            master_key=master_key,
        )

    def finish_password_change(self, user: VaultUser, password: str) -> VaultUnlockResult:
        result = self._migrate_legacy_entries(user, str(password or "").strip())
        self._complete_legacy_scrub(user)
        unlock_result = VaultUnlockResult(
            migrated_entries=result[0],
            migration_backup=result[1],
            os_protection=self.protector.name,
        )
        self._last_results[self._owner_key(user.username)] = unlock_result
        return unlock_result

    def lock(self, owner: str) -> None:
        cached = self._unlocked.pop(self._owner_key(owner), None)
        if cached is not None:
            for index in range(len(cached.key)):
                cached.key[index] = 0

    def lock_all(self) -> None:
        for owner in tuple(self._unlocked):
            self.lock(owner)

    def encrypt_text(
        self,
        owner: str,
        crypto_id: str,
        field: str,
        value: str,
    ) -> EncryptedValue:
        key = bytes(self._key_for(owner))
        nonce = secrets.token_bytes(_NONCE_BYTES)
        ciphertext = AESGCM(key).encrypt(
            nonce,
            str(value).encode("utf-8"),
            self._field_aad(owner, crypto_id, field),
        )
        return EncryptedValue(nonce=nonce, ciphertext=ciphertext)

    def decrypt_text(
        self,
        owner: str,
        crypto_id: str,
        field: str,
        nonce: bytes,
        ciphertext: bytes,
    ) -> str:
        key = bytes(self._key_for(owner))
        try:
            plaintext = AESGCM(key).decrypt(
                bytes(nonce),
                bytes(ciphertext),
                self._field_aad(owner, crypto_id, field),
            )
            return plaintext.decode("utf-8")
        except (InvalidTag, UnicodeDecodeError, TypeError, ValueError) as exc:
            raise JournalVaultIntegrityError(
                "Não foi possível validar uma entrada do diário. O banco pode ter sido "
                "alterado/corrompido; nenhum conteúdo inseguro foi exibido."
            ) from exc

    def blind_token(self, owner: str, token: str) -> str:
        key = bytes(self._key_for(owner))
        search_key = hmac.new(
            key,
            b"HULI journal blind-index key v1",
            hashlib.sha256,
        ).digest()
        return hmac.new(
            search_key,
            str(token).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    @staticmethod
    def new_crypto_id() -> str:
        return uuid4().hex

    def _key_for(self, owner: str, *, touch: bool = True) -> bytearray:
        owner_key = self._owner_key(owner)
        cached = self._unlocked.get(owner_key)
        now = self._clock()
        if cached is None:
            raise JournalVaultLockedError(
                "O cofre do diário está bloqueado. Saia e autentique novamente."
            )
        if now - cached.last_used >= self.inactivity_seconds:
            self.lock(owner)
            raise JournalVaultLockedError(
                "O cofre do diário foi bloqueado por inatividade. Autentique novamente."
            )
        if touch:
            cached.last_used = now
        return cached.key

    def _cache_key(self, user: VaultUser, master_key: bytes) -> None:
        self.lock(user.username)
        self._unlocked[self._owner_key(user.username)] = _UnlockedKey(
            user_id=user.id,
            owner=user.username,
            key=bytearray(master_key),
            last_used=self._clock(),
        )

    @staticmethod
    def _vault_row(connection: sqlite3.Connection, user_id: int) -> sqlite3.Row | None:
        return connection.execute(
            "SELECT * FROM journal_vaults WHERE user_id = ?",
            (int(user_id),),
        ).fetchone()

    def _insert_vault(
        self,
        connection: sqlite3.Connection,
        user: VaultUser,
        password: str,
        master_key: bytes,
    ) -> None:
        salt = secrets.token_bytes(16)
        wrapped_nonce, wrapped_key = self._wrap_master_key(
            master_key,
            password=password,
            salt=salt,
            user_id=user.id,
        )
        now = datetime.now(timezone.utc).isoformat()
        legacy_row = connection.execute(
            """
            SELECT COUNT(*) AS total
            FROM journal_entries
            WHERE owner = ? COLLATE NOCASE
              AND COALESCE(crypto_version, 0) = 0
            """,
            (user.username,),
        ).fetchone()
        scrub_required = bool(legacy_row and int(legacy_row["total"]) > 0)
        connection.execute(
            """
            INSERT INTO journal_vaults(
                user_id, kdf_salt, kdf_n, kdf_r, kdf_p,
                wrapped_nonce, wrapped_key, os_protection,
                crypto_version, legacy_scrub_required, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user.id,
                salt,
                _KDF_N,
                _KDF_R,
                _KDF_P,
                wrapped_nonce,
                wrapped_key,
                self.protector.name,
                _CRYPTO_VERSION,
                1 if scrub_required else 0,
                now,
                now,
            ),
        )

    def _wrap_master_key(
        self,
        master_key: bytes,
        *,
        password: str,
        salt: bytes,
        user_id: int,
    ) -> tuple[bytes, bytes]:
        kek = self._derive_kek(password, salt, n=_KDF_N, r=_KDF_R, p=_KDF_P)
        nonce = secrets.token_bytes(_NONCE_BYTES)
        password_wrapped = AESGCM(kek).encrypt(
            nonce,
            bytes(master_key),
            self._vault_aad(user_id),
        )
        try:
            return nonce, self.protector.protect(password_wrapped)
        except OSProtectionError as exc:
            raise JournalVaultError(str(exc)) from exc

    def _update_wrapped_key(
        self,
        connection: sqlite3.Connection,
        user: VaultUser,
        *,
        password: str,
        master_key: bytes,
    ) -> None:
        salt = secrets.token_bytes(16)
        wrapped_nonce, wrapped_key = self._wrap_master_key(
            master_key,
            password=password,
            salt=salt,
            user_id=user.id,
        )
        connection.execute(
            """
            UPDATE journal_vaults
            SET kdf_salt = ?, kdf_n = ?, kdf_r = ?, kdf_p = ?,
                wrapped_nonce = ?, wrapped_key = ?, os_protection = ?,
                updated_at = ?
            WHERE user_id = ?
            """,
            (
                salt,
                _KDF_N,
                _KDF_R,
                _KDF_P,
                wrapped_nonce,
                wrapped_key,
                self.protector.name,
                datetime.now(timezone.utc).isoformat(),
                user.id,
            ),
        )

    def _unwrap_master_key(
        self,
        row: sqlite3.Row,
        user: VaultUser,
        password: str,
    ) -> bytes:
        protection = str(row["os_protection"])
        if protection == self.protector.name:
            protector = self.protector
        elif protection == PasswordOnlyProtector.name:
            protector = PasswordOnlyProtector()
        else:
            raise JournalVaultError(
                "A proteção do cofre não está disponível neste sistema/usuário. "
                "Use o backup portátil criptografado para recuperação."
            )
        try:
            password_wrapped = protector.unprotect(bytes(row["wrapped_key"]))
        except OSProtectionError as exc:
            raise JournalVaultError(str(exc)) from exc
        # A senha foi validada pelo AuthService; o envelope ainda é autenticado
        # novamente aqui para detectar corrupção ou inconsistência de chave.
        kek = self._derive_kek(
            password,
            bytes(row["kdf_salt"]),
            n=int(row["kdf_n"]),
            r=int(row["kdf_r"]),
            p=int(row["kdf_p"]),
        )
        try:
            master_key = AESGCM(kek).decrypt(
                bytes(row["wrapped_nonce"]),
                password_wrapped,
                self._vault_aad(user.id),
            )
        except (InvalidTag, ValueError, TypeError) as exc:
            raise JournalVaultIntegrityError(
                "Não foi possível abrir o cofre. A senha, a conta do sistema ou o banco "
                "não correspondem ao envelope original."
            ) from exc
        if len(master_key) != _KEY_BYTES:
            raise JournalVaultIntegrityError("Tamanho de chave inválido no cofre.")
        return master_key

    def _migrate_legacy_entries(
        self,
        user: VaultUser,
        password: str,
    ) -> tuple[int, Path | None]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM journal_entries
                WHERE owner = ? COLLATE NOCASE
                  AND COALESCE(crypto_version, 0) = 0
                ORDER BY id
                """,
                (user.username,),
            ).fetchall()
        if not rows:
            return 0, None

        backup_path = self._write_migration_backup(user, password, rows)
        with self.database.connect() as connection:
            for row in rows:
                crypto_id = self.new_crypto_id()
                content = str(row["content"])
                search_text = str(row["search_text"])
                mood = str(row["mood"]) if row["mood"] is not None else ""
                tags_json = str(row["tags_json"] or "[]")
                encrypted = {
                    "content": self.encrypt_text(
                        user.username, crypto_id, "content", content
                    ),
                    "search": self.encrypt_text(
                        user.username, crypto_id, "search", search_text
                    ),
                    "mood": self.encrypt_text(user.username, crypto_id, "mood", mood),
                    "tags": self.encrypt_text(
                        user.username, crypto_id, "tags", tags_json
                    ),
                }
                connection.execute(
                    """
                    UPDATE journal_entries
                    SET content = '', search_text = '', mood = NULL, tags_json = '[]',
                        crypto_id = ?, content_nonce = ?, content_ciphertext = ?,
                        search_nonce = ?, search_ciphertext = ?,
                        mood_nonce = ?, mood_ciphertext = ?,
                        tags_nonce = ?, tags_ciphertext = ?, crypto_version = ?
                    WHERE id = ? AND owner = ? COLLATE NOCASE
                      AND COALESCE(crypto_version, 0) = 0
                    """,
                    (
                        crypto_id,
                        encrypted["content"].nonce,
                        encrypted["content"].ciphertext,
                        encrypted["search"].nonce,
                        encrypted["search"].ciphertext,
                        encrypted["mood"].nonce,
                        encrypted["mood"].ciphertext,
                        encrypted["tags"].nonce,
                        encrypted["tags"].ciphertext,
                        _CRYPTO_VERSION,
                        int(row["id"]),
                        user.username,
                    ),
                )
                self._replace_search_tokens(
                    connection,
                    entry_id=int(row["id"]),
                    owner=user.username,
                    search_text=search_text,
                )
        return len(rows), backup_path

    def _complete_legacy_scrub(self, user: VaultUser) -> None:
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT legacy_scrub_required
                FROM journal_vaults
                WHERE user_id = ?
                """,
                (user.id,),
            ).fetchone()
        if row is None or not bool(row["legacy_scrub_required"]):
            return

        # A transação de cifragem já terminou. O VACUUM remove páginas antigas
        # do arquivo lógico e o checkpoint trunca cópias residuais do WAL.
        self.database.secure_compact()
        with self.database.connect() as connection:
            connection.execute(
                """
                UPDATE journal_vaults
                SET legacy_scrub_required = 0, legacy_scrubbed_at = ?, updated_at = ?
                WHERE user_id = ?
                """,
                (
                    datetime.now(timezone.utc).isoformat(),
                    datetime.now(timezone.utc).isoformat(),
                    user.id,
                ),
            )

    def _write_migration_backup(
        self,
        user: VaultUser,
        password: str,
        rows: list[sqlite3.Row],
    ) -> Path:
        entries = []
        for row in rows:
            entries.append(
                {
                    "id": int(row["id"]),
                    "owner": str(row["owner"]),
                    "content": str(row["content"]),
                    "search_text": str(row["search_text"]),
                    "entry_date": str(row["entry_date"]),
                    "mood": str(row["mood"]) if row["mood"] is not None else None,
                    "tags_json": str(row["tags_json"] or "[]"),
                    "sensitivity": str(row["sensitivity"]),
                    "created_at": str(row["created_at"]),
                    "updated_at": str(row["updated_at"]),
                    "deleted_at": (
                        str(row["deleted_at"]) if row["deleted_at"] is not None else None
                    ),
                    "is_active": bool(row["is_active"]),
                }
            )
        envelope = seal_json(
            {"schema": 7, "entries": entries},
            password=password,
            owner=user.username,
            purpose="journal-plaintext-migration",
        )
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        safe_owner = re.sub(r"[^A-Za-z0-9_.-]+", "_", user.username).strip("._")
        safe_owner = safe_owner or f"user-{user.id}"
        path = (
            self.database.path.parent
            / "backups"
            / f"journal-pre-alpha12-{safe_owner}-{stamp}.hulibak"
        )
        return write_envelope(path, envelope)

    def _replace_search_tokens(
        self,
        connection: sqlite3.Connection,
        *,
        entry_id: int,
        owner: str,
        search_text: str,
    ) -> None:
        connection.execute(
            "DELETE FROM journal_search_tokens WHERE entry_id = ?",
            (entry_id,),
        )
        tokens = tuple(dict.fromkeys(str(search_text).split()))
        connection.executemany(
            """
            INSERT INTO journal_search_tokens(entry_id, token_hash)
            VALUES (?, ?)
            """,
            ((entry_id, self.blind_token(owner, token)) for token in tokens),
        )

    @staticmethod
    def _derive_kek(password: str, salt: bytes, *, n: int, r: int, p: int) -> bytes:
        if not password:
            raise JournalVaultLockedError("O cofre exige uma senha não vazia.")
        if (n, r, p) != (_KDF_N, _KDF_R, _KDF_P):
            raise JournalVaultError("Parâmetros criptográficos do cofre não suportados.")
        return hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=n,
            r=r,
            p=p,
            dklen=_KEY_BYTES,
        )

    @staticmethod
    def _vault_aad(user_id: int) -> bytes:
        return f"HULI journal vault|v{_CRYPTO_VERSION}|user:{user_id}".encode("utf-8")

    @staticmethod
    def _field_aad(owner: str, crypto_id: str, field: str) -> bytes:
        return (
            f"HULI journal entry|v{_CRYPTO_VERSION}|{owner.casefold()}|"
            f"{crypto_id}|{field}"
        ).encode("utf-8")


__all__ = [
    "EncryptedValue",
    "JournalVault",
    "JournalVaultError",
    "JournalVaultIntegrityError",
    "JournalVaultLockedError",
    "VaultUnlockResult",
]
