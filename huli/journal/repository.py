"""Persistência do diário, sempre isolada pelo proprietário."""

from __future__ import annotations

from datetime import date, datetime, timezone
import json
import sqlite3

from huli.infrastructure.database import SQLiteDatabase
from huli.journal.models import JournalEntry, JournalSensitivity
from huli.journal.normalization import normalize_journal_text


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_datetime(value: object) -> datetime | None:
    if value in (None, ""):
        return None
    return datetime.fromisoformat(str(value))


class JournalRepository:
    """CRUD lógico do diário sem consultas que atravessem proprietários."""

    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database

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
        with self.database.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO journal_entries(
                    owner, content, search_text, entry_date, mood, tags_json,
                    sensitivity, created_at, updated_at, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                """,
                (
                    owner,
                    content,
                    search_text,
                    entry_date.isoformat(),
                    mood,
                    json.dumps(tags, ensure_ascii=False),
                    sensitivity.value,
                    now,
                    now,
                ),
            )
            entry_id = int(cursor.lastrowid)
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
        safe_limit = max(1, min(int(limit), 100))
        clauses = [
            "owner = ? COLLATE NOCASE",
            "is_active = 1",
        ]
        clauses.extend("search_text LIKE ?" for _token in tokens)
        params: list[object] = [owner, *(f"%{token}%" for token in tokens)]
        if start_date is not None:
            clauses.append("entry_date >= ?")
            params.append(start_date.isoformat())
        if end_date is not None:
            clauses.append("entry_date <= ?")
            params.append(end_date.isoformat())
        params.append(safe_limit)
        sql = f"""
            SELECT * FROM journal_entries
            WHERE {' AND '.join(clauses)}
            ORDER BY entry_date DESC, created_at DESC, id DESC
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
        with self.database.connect() as connection:
            connection.execute(
                """
                UPDATE journal_entries
                SET content = ?, search_text = ?, mood = ?, tags_json = ?,
                    sensitivity = ?, updated_at = ?
                WHERE id = ? AND owner = ? COLLATE NOCASE AND is_active = 1
                """,
                (
                    content,
                    search_text,
                    mood,
                    json.dumps(tags, ensure_ascii=False),
                    sensitivity.value,
                    _now_iso(),
                    int(entry_id),
                    owner,
                ),
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

    @staticmethod
    def _from_row(row: sqlite3.Row) -> JournalEntry:
        try:
            raw_tags = json.loads(str(row["tags_json"] or "[]"))
        except json.JSONDecodeError:
            raw_tags = []
        tags = tuple(str(tag) for tag in raw_tags) if isinstance(raw_tags, list) else ()
        return JournalEntry(
            id=int(row["id"]),
            owner=str(row["owner"]),
            content=str(row["content"]),
            search_text=str(row["search_text"]),
            entry_date=date.fromisoformat(str(row["entry_date"])),
            mood=str(row["mood"]) if row["mood"] is not None else None,
            tags=tags,
            sensitivity=JournalSensitivity(str(row["sensitivity"])),
            created_at=datetime.fromisoformat(str(row["created_at"])),
            updated_at=datetime.fromisoformat(str(row["updated_at"])),
            deleted_at=_parse_datetime(row["deleted_at"]),
            is_active=bool(row["is_active"]),
        )


__all__ = ["JournalRepository"]
