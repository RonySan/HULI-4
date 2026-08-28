"""Persistência das memórias de longo prazo da Huli."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import sqlite3

from huli.infrastructure.database import SQLiteDatabase
from huli.memory.models import (
    MemoryKind,
    MemoryRecord,
    MemorySensitivity,
    MemorySource,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_datetime(value: object) -> datetime | None:
    if value in (None, ""):
        return None
    return datetime.fromisoformat(str(value))


class MemoryRepository:
    """CRUD lógico e consultas de memória isoladas por proprietário."""

    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database

    def upsert(
        self,
        *,
        owner: str,
        kind: MemoryKind,
        content: str,
        normalized_content: str,
        subject: str | None,
        project: str | None,
        sensitivity: MemorySensitivity,
        source: MemorySource,
        confidence: float,
        occurred_at: datetime | None,
        valid_until: datetime | None,
        metadata: dict[str, object] | None = None,
    ) -> tuple[MemoryRecord, bool]:
        now = _now_iso()
        metadata_json = json.dumps(metadata or {}, ensure_ascii=False, sort_keys=True)
        with self.database.connect() as connection:
            existing = connection.execute(
                """
                SELECT id
                FROM memories
                WHERE owner = ? COLLATE NOCASE
                  AND kind = ?
                  AND normalized_content = ?
                  AND COALESCE(subject, '') = COALESCE(?, '')
                  AND COALESCE(project, '') = COALESCE(?, '')
                  AND is_active = 1
                LIMIT 1
                """,
                (owner, kind.value, normalized_content, subject, project),
            ).fetchone()

            if existing is not None:
                memory_id = int(existing["id"])
                connection.execute(
                    """
                    UPDATE memories
                    SET content = ?,
                        sensitivity = ?,
                        source = ?,
                        confidence = MAX(confidence, ?),
                        occurred_at = COALESCE(?, occurred_at),
                        valid_until = COALESCE(?, valid_until),
                        metadata_json = ?,
                        updated_at = ?
                    WHERE id = ? AND owner = ? COLLATE NOCASE
                    """,
                    (
                        content,
                        sensitivity.value,
                        source.value,
                        float(confidence),
                        occurred_at.isoformat() if occurred_at else None,
                        valid_until.isoformat() if valid_until else None,
                        metadata_json,
                        now,
                        memory_id,
                        owner,
                    ),
                )
                return self.get(memory_id, owner), False

            cursor = connection.execute(
                """
                INSERT INTO memories(
                    owner, kind, content, normalized_content, subject, project,
                    sensitivity, source, confidence, occurred_at, valid_until,
                    metadata_json, created_at, updated_at, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                """,
                (
                    owner,
                    kind.value,
                    content,
                    normalized_content,
                    subject,
                    project,
                    sensitivity.value,
                    source.value,
                    float(confidence),
                    occurred_at.isoformat() if occurred_at else None,
                    valid_until.isoformat() if valid_until else None,
                    metadata_json,
                    now,
                    now,
                ),
            )
            memory_id = int(cursor.lastrowid)

        return self.get(memory_id, owner), True

    def get(self, memory_id: int, owner: str) -> MemoryRecord:
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM memories
                WHERE id = ? AND owner = ? COLLATE NOCASE
                """,
                (int(memory_id), owner),
            ).fetchone()
        if row is None:
            raise LookupError("Memória não encontrada.")
        return self._from_row(row)

    def list_active(
        self,
        owner: str,
        *,
        kind: MemoryKind | None = None,
        project: str | None = None,
        limit: int = 50,
    ) -> tuple[MemoryRecord, ...]:
        safe_limit = max(1, min(int(limit), 200))
        clauses = ["owner = ? COLLATE NOCASE", "is_active = 1"]
        params: list[object] = [owner]
        if kind is not None:
            clauses.append("kind = ?")
            params.append(kind.value)
        if project is not None:
            clauses.append("project = ? COLLATE NOCASE")
            params.append(project)
        params.append(safe_limit)
        sql = f"""
            SELECT * FROM memories
            WHERE {' AND '.join(clauses)}
            ORDER BY updated_at DESC, id DESC
            LIMIT ?
        """
        with self.database.connect() as connection:
            rows = connection.execute(sql, tuple(params)).fetchall()
        return tuple(self._from_row(row) for row in rows)

    def forget(self, memory_id: int, owner: str) -> MemoryRecord:
        memory = self.get(memory_id, owner)
        if not memory.is_active:
            return memory
        now = _now_iso()
        with self.database.connect() as connection:
            connection.execute(
                """
                UPDATE memories
                SET is_active = 0, updated_at = ?
                WHERE id = ? AND owner = ? COLLATE NOCASE
                """,
                (now, int(memory_id), owner),
            )
        return self.get(memory_id, owner)

    def record_access(self, memory_id: int, owner: str) -> None:
        now = _now_iso()
        with self.database.connect() as connection:
            connection.execute(
                """
                UPDATE memories
                SET access_count = access_count + 1,
                    last_accessed_at = ?
                WHERE id = ? AND owner = ? COLLATE NOCASE AND is_active = 1
                """,
                (now, int(memory_id), owner),
            )

    def count_active(self, owner: str) -> int:
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS total
                FROM memories
                WHERE owner = ? COLLATE NOCASE AND is_active = 1
                """,
                (owner,),
            ).fetchone()
        return int(row["total"]) if row else 0

    @staticmethod
    def _from_row(row: sqlite3.Row) -> MemoryRecord:
        try:
            metadata = json.loads(str(row["metadata_json"] or "{}"))
        except json.JSONDecodeError:
            metadata = {}
        return MemoryRecord(
            id=int(row["id"]),
            owner=str(row["owner"]),
            kind=MemoryKind(str(row["kind"])),
            content=str(row["content"]),
            normalized_content=str(row["normalized_content"]),
            subject=str(row["subject"]) if row["subject"] is not None else None,
            project=str(row["project"]) if row["project"] is not None else None,
            sensitivity=MemorySensitivity(str(row["sensitivity"])),
            source=MemorySource(str(row["source"])),
            confidence=float(row["confidence"]),
            occurred_at=_parse_datetime(row["occurred_at"]),
            valid_until=_parse_datetime(row["valid_until"]),
            created_at=datetime.fromisoformat(str(row["created_at"])),
            updated_at=datetime.fromisoformat(str(row["updated_at"])),
            last_accessed_at=_parse_datetime(row["last_accessed_at"]),
            access_count=int(row["access_count"]),
            is_active=bool(row["is_active"]),
            metadata=metadata if isinstance(metadata, dict) else {},
        )
