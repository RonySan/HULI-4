"""Persistência cifrada do diário, sempre isolada pelo proprietário."""

from __future__ import annotations

from datetime import date, datetime, timezone
import json
import sqlite3

from huli.infrastructure.database import SQLiteDatabase
from huli.journal.models import JournalEntry, JournalSensitivity
from huli.journal.normalization import normalize_journal_text
from huli.security.journal_vault import JournalVault, JournalVaultIntegrityError


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_datetime(value: object) -> datetime | None:
    if value in (None, ""):
        return None
    return datetime.fromisoformat(str(value))


class JournalRepository:
    """CRUD cifrado sem consultas que atravessem proprietários."""

    def __init__(self, database: SQLiteDatabase, vault: JournalVault) -> None:
        self.database = database
        self.vault = vault

    def create(
        self,
        *,
        owner: str,
        content: str,
        search_text: str,
        entry_date: date,
        mood: str | None,
        tags: tuple[str, ...],
        sensitivity: JournalSensitivity,
    ) -> JournalEntry:
        now = _now_iso()
        crypto_id = self.vault.new_crypto_id()
        encrypted = self._encrypt_fields(
            owner=owner,
            crypto_id=crypto_id,
            content=content,
            search_text=search_text,
            mood=mood,
            tags=tags,
        )
        with self.database.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO journal_entries(
                    owner, content, search_text, entry_date, mood, tags_json,
                    sensitivity, created_at, updated_at, is_active,
                    crypto_id, content_nonce, content_ciphertext,
                    search_nonce, search_ciphertext, mood_nonce, mood_ciphertext,
                    tags_nonce, tags_ciphertext, crypto_version
                ) VALUES (?, '', '', ?, NULL, '[]', ?, ?, ?, 1,
                          ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                """,
                (
                    owner,
                    entry_date.isoformat(),
                    sensitivity.value,
                    now,
                    now,
                    crypto_id,
                    encrypted["content"].nonce,
                    encrypted["content"].ciphertext,
                    encrypted["search"].nonce,
                    encrypted["search"].ciphertext,
                    encrypted["mood"].nonce,
                    encrypted["mood"].ciphertext,
                    encrypted["tags"].nonce,
                    encrypted["tags"].ciphertext,
                ),
            )
            entry_id = int(cursor.lastrowid)
            self._replace_search_tokens(
                connection,
                entry_id=entry_id,
                owner=owner,
                search_text=search_text,
            )
        return self.get(entry_id, owner)

    def get(self, entry_id: int, owner: str) -> JournalEntry:
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM journal_entries
                WHERE id = ? AND owner = ? COLLATE NOCASE
                """,
                (int(entry_id), owner),
            ).fetchone()
        if row is None:
            raise LookupError("Entrada do diário não encontrada.")
        return self._from_row(row)

    def list_entries(
        self,
        owner: str,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 20,
    ) -> tuple[JournalEntry, ...]:
        safe_limit = max(1, min(int(limit), 100))
        clauses = ["owner = ? COLLATE NOCASE", "is_active = 1"]
        params: list[object] = [owner]
        if start_date is not None:
            clauses.append("entry_date >= ?")
            params.append(start_date.isoformat())
        if end_date is not None:
            clauses.append("entry_date <= ?")
            params.append(end_date.isoformat())
        params.append(safe_limit)
        query = f"""
            SELECT * FROM journal_entries
            WHERE {' AND '.join(clauses)}
            ORDER BY entry_date DESC, created_at DESC, id DESC
            LIMIT ?
        """
        with self.database.connect() as connection:
            rows = connection.execute(query, tuple(params)).fetchall()
        return tuple(self._from_row(row) for row in rows)

    def search(
        self,
        owner: str,
        query: str,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 20,
    ) -> tuple[JournalEntry, ...]:
        normalized = normalize_journal_text(query)
        if not normalized:
            return ()
        tokens = tuple(dict.fromkeys(normalized.split()))
        token_hashes = tuple(self.vault.blind_token(owner, token) for token in tokens)
        safe_limit = max(1, min(int(limit), 100))
        placeholders = ", ".join("?" for _token in token_hashes)
        clauses = [
            "je.owner = ? COLLATE NOCASE",
            "je.is_active = 1",
            f"st.token_hash IN ({placeholders})",
        ]
        params: list[object] = [owner, *token_hashes]
        if start_date is not None:
            clauses.append("je.entry_date >= ?")
            params.append(start_date.isoformat())
        if end_date is not None:
            clauses.append("je.entry_date <= ?")
            params.append(end_date.isoformat())
        params.extend((len(token_hashes), safe_limit))
        sql = f"""
            SELECT je.*
            FROM journal_entries je
            JOIN journal_search_tokens st ON st.entry_id = je.id
            WHERE {' AND '.join(clauses)}
            GROUP BY je.id
            HAVING COUNT(DISTINCT st.token_hash) = ?
            ORDER BY je.entry_date DESC, je.created_at DESC, je.id DESC
            LIMIT ?
        """
        with self.database.connect() as connection:
            rows = connection.execute(sql, tuple(params)).fetchall()
        return tuple(self._from_row(row) for row in rows)

    def list_deleted(self, owner: str, *, limit: int = 20) -> tuple[JournalEntry, ...]:
        safe_limit = max(1, min(int(limit), 100))
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM journal_entries
                WHERE owner = ? COLLATE NOCASE AND is_active = 0
                ORDER BY deleted_at DESC, id DESC
                LIMIT ?
                """,
                (owner, safe_limit),
            ).fetchall()
        return tuple(self._from_row(row) for row in rows)

    def all_entries(self, owner: str) -> tuple[JournalEntry, ...]:
        """Inclui lixeira; usado exclusivamente por backup autenticado."""

        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM journal_entries
                WHERE owner = ? COLLATE NOCASE
                ORDER BY id
                """,
                (owner,),
            ).fetchall()
        return tuple(self._from_row(row) for row in rows)

    def update(
        self,
        *,
        entry_id: int,
        owner: str,
        content: str,
        search_text: str,
        mood: str | None,
        tags: tuple[str, ...],
        sensitivity: JournalSensitivity,
    ) -> JournalEntry:
        current = self.get(entry_id, owner)
        if not current.is_active:
            raise LookupError("Essa entrada do diário já foi apagada.")
        crypto_id = self.vault.new_crypto_id()
        encrypted = self._encrypt_fields(
            owner=owner,
            crypto_id=crypto_id,
            content=content,
            search_text=search_text,
            mood=mood,
            tags=tags,
        )
        with self.database.connect() as connection:
            connection.execute(
                """
                UPDATE journal_entries
                SET content = '', search_text = '', mood = NULL, tags_json = '[]',
                    sensitivity = ?, updated_at = ?, crypto_id = ?,
                    content_nonce = ?, content_ciphertext = ?,
                    search_nonce = ?, search_ciphertext = ?,
                    mood_nonce = ?, mood_ciphertext = ?,
                    tags_nonce = ?, tags_ciphertext = ?, crypto_version = 1
                WHERE id = ? AND owner = ? COLLATE NOCASE AND is_active = 1
                """,
                (
                    sensitivity.value,
                    _now_iso(),
                    crypto_id,
                    encrypted["content"].nonce,
                    encrypted["content"].ciphertext,
                    encrypted["search"].nonce,
                    encrypted["search"].ciphertext,
                    encrypted["mood"].nonce,
                    encrypted["mood"].ciphertext,
                    encrypted["tags"].nonce,
                    encrypted["tags"].ciphertext,
                    int(entry_id),
                    owner,
                ),
            )
            self._replace_search_tokens(
                connection,
                entry_id=int(entry_id),
                owner=owner,
                search_text=search_text,
            )
        return self.get(entry_id, owner)

    def delete(self, entry_id: int, owner: str) -> JournalEntry:
        current = self.get(entry_id, owner)
        if not current.is_active:
            return current
        now = _now_iso()
        with self.database.connect() as connection:
            connection.execute(
                """
                UPDATE journal_entries
                SET is_active = 0, deleted_at = ?, updated_at = ?
                WHERE id = ? AND owner = ? COLLATE NOCASE
                """,
                (now, now, int(entry_id), owner),
            )
        return self.get(entry_id, owner)

    def restore(self, entry_id: int, owner: str) -> JournalEntry:
        current = self.get(entry_id, owner)
        if current.is_active:
            return current
        with self.database.connect() as connection:
            connection.execute(
                """
                UPDATE journal_entries
                SET is_active = 1, deleted_at = NULL, updated_at = ?
                WHERE id = ? AND owner = ? COLLATE NOCASE
                """,
                (_now_iso(), int(entry_id), owner),
            )
        return self.get(entry_id, owner)

    def count_active(self, owner: str) -> int:
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS total FROM journal_entries
                WHERE owner = ? COLLATE NOCASE AND is_active = 1
                """,
                (owner,),
            ).fetchone()
        return int(row["total"]) if row else 0

    def count_all(self, owner: str) -> int:
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS total FROM journal_entries
                WHERE owner = ? COLLATE NOCASE
                """,
                (owner,),
            ).fetchone()
        return int(row["total"]) if row else 0

    def replace_all(self, owner: str, entries: tuple[JournalEntry, ...]) -> int:
        """Restaura após confirmação externa, atribuindo novos IDs sem colisão."""

        prepared: list[tuple[JournalEntry, str, dict[str, object]]] = []
        for entry in entries:
            crypto_id = self.vault.new_crypto_id()
            prepared.append(
                (
                    entry,
                    crypto_id,
                    self._encrypt_fields(
                        owner=owner,
                        crypto_id=crypto_id,
                        content=entry.content,
                        search_text=entry.search_text,
                        mood=entry.mood,
                        tags=entry.tags,
                    ),
                )
            )
        with self.database.connect() as connection:
            connection.execute(
                "DELETE FROM journal_entries WHERE owner = ? COLLATE NOCASE",
                (owner,),
            )
            for entry, crypto_id, encrypted in prepared:
                cursor = connection.execute(
                    """
                    INSERT INTO journal_entries(
                        owner, content, search_text, entry_date, mood, tags_json,
                        sensitivity, created_at, updated_at, deleted_at, is_active,
                        crypto_id, content_nonce, content_ciphertext,
                        search_nonce, search_ciphertext, mood_nonce, mood_ciphertext,
                        tags_nonce, tags_ciphertext, crypto_version
                    ) VALUES (?, '', '', ?, NULL, '[]', ?, ?, ?, ?, ?,
                              ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                    """,
                    (
                        owner,
                        entry.entry_date.isoformat(),
                        entry.sensitivity.value,
                        entry.created_at.isoformat(),
                        entry.updated_at.isoformat(),
                        entry.deleted_at.isoformat() if entry.deleted_at else None,
                        1 if entry.is_active else 0,
                        crypto_id,
                        encrypted["content"].nonce,
                        encrypted["content"].ciphertext,
                        encrypted["search"].nonce,
                        encrypted["search"].ciphertext,
                        encrypted["mood"].nonce,
                        encrypted["mood"].ciphertext,
                        encrypted["tags"].nonce,
                        encrypted["tags"].ciphertext,
                    ),
                )
                self._replace_search_tokens(
                    connection,
                    entry_id=int(cursor.lastrowid),
                    owner=owner,
                    search_text=entry.search_text,
                )
        return len(entries)

    def _encrypt_fields(
        self,
        *,
        owner: str,
        crypto_id: str,
        content: str,
        search_text: str,
        mood: str | None,
        tags: tuple[str, ...],
    ) -> dict[str, object]:
        return {
            "content": self.vault.encrypt_text(owner, crypto_id, "content", content),
            "search": self.vault.encrypt_text(owner, crypto_id, "search", search_text),
            "mood": self.vault.encrypt_text(owner, crypto_id, "mood", mood or ""),
            "tags": self.vault.encrypt_text(
                owner,
                crypto_id,
                "tags",
                json.dumps(tags, ensure_ascii=False),
            ),
        }

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
        tokens = tuple(dict.fromkeys(normalize_journal_text(search_text).split()))
        connection.executemany(
            """
            INSERT INTO journal_search_tokens(entry_id, token_hash)
            VALUES (?, ?)
            """,
            ((entry_id, self.vault.blind_token(owner, token)) for token in tokens),
        )

    def _from_row(self, row: sqlite3.Row) -> JournalEntry:
        if int(row["crypto_version"] or 0) != 1 or not row["crypto_id"]:
            raise JournalVaultIntegrityError(
                "A entrada legada ainda não foi migrada. Autentique novamente para "
                "executar a migração protegida."
            )
        owner = str(row["owner"])
        crypto_id = str(row["crypto_id"])
        content = self._decrypt_column(row, owner, crypto_id, "content")
        search_text = self._decrypt_column(row, owner, crypto_id, "search")
        mood_text = self._decrypt_column(row, owner, crypto_id, "mood")
        tags_text = self._decrypt_column(row, owner, crypto_id, "tags")
        try:
            raw_tags = json.loads(tags_text or "[]")
        except json.JSONDecodeError as exc:
            raise JournalVaultIntegrityError(
                "As etiquetas cifradas do diário estão corrompidas."
            ) from exc
        tags = tuple(str(tag) for tag in raw_tags) if isinstance(raw_tags, list) else ()
        return JournalEntry(
            id=int(row["id"]),
            owner=owner,
            content=content,
            search_text=search_text,
            entry_date=date.fromisoformat(str(row["entry_date"])),
            mood=mood_text or None,
            tags=tags,
            sensitivity=JournalSensitivity(str(row["sensitivity"])),
            created_at=datetime.fromisoformat(str(row["created_at"])),
            updated_at=datetime.fromisoformat(str(row["updated_at"])),
            deleted_at=_parse_datetime(row["deleted_at"]),
            is_active=bool(row["is_active"]),
        )

    def _decrypt_column(
        self,
        row: sqlite3.Row,
        owner: str,
        crypto_id: str,
        field: str,
    ) -> str:
        nonce = row[f"{field}_nonce"]
        ciphertext = row[f"{field}_ciphertext"]
        if nonce is None or ciphertext is None:
            raise JournalVaultIntegrityError(
                "Uma entrada cifrada do diário está incompleta."
            )
        return self.vault.decrypt_text(
            owner,
            crypto_id,
            field,
            bytes(nonce),
            bytes(ciphertext),
        )


__all__ = ["JournalRepository"]
