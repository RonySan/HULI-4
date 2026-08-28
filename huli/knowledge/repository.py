"""Persistência SQLite do Personal Knowledge Graph."""

from __future__ import annotations

from datetime import datetime, timezone
import sqlite3

from huli.infrastructure import SQLiteDatabase
from huli.knowledge.models import EntityKind, KnowledgeEntity, KnowledgeFact, KnowledgeRelation
from huli.knowledge.normalization import normalize_knowledge_text
from huli.memory import MemorySensitivity


_SENSITIVITY_RANK = {
    MemorySensitivity.NORMAL: 0,
    MemorySensitivity.SENSITIVE: 1,
    MemorySensitivity.SECRET: 2,
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    return value.astimezone(timezone.utc).isoformat() if value is not None else None


def _dt(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


class KnowledgeRepository:
    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database

    def upsert_entity(
        self,
        *,
        owner: str,
        name: str,
        kind: EntityKind,
        sensitivity: MemorySensitivity = MemorySensitivity.NORMAL,
        source_memory_id: int | None = None,
    ) -> KnowledgeEntity:
        clean_name = " ".join(str(name or "").split()).strip(" .,-:;")
        normalized = normalize_knowledge_text(clean_name)
        if not clean_name or not normalized:
            raise ValueError("A entidade precisa ter um nome válido.")
        now = _now()
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM knowledge_entities
                WHERE owner = ? COLLATE NOCASE
                  AND normalized_name = ?
                  AND kind = ?
                ORDER BY is_active DESC, id ASC
                LIMIT 1
                """,
                (owner, normalized, kind.value),
            ).fetchone()
            if row is None:
                cursor = connection.execute(
                    """
                    INSERT INTO knowledge_entities(
                        owner, name, normalized_name, kind, sensitivity,
                        manual_source, created_at, updated_at, is_active
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
                    """,
                    (
                        owner,
                        clean_name,
                        normalized,
                        kind.value,
                        sensitivity.value,
                        1 if source_memory_id is None else 0,
                        _iso(now),
                        _iso(now),
                    ),
                )
                entity_id = int(cursor.lastrowid)
            else:
                entity_id = int(row["id"])
                current = MemorySensitivity(str(row["sensitivity"]))
                resolved = (
                    sensitivity
                    if _SENSITIVITY_RANK[sensitivity] > _SENSITIVITY_RANK[current]
                    else current
                )
                connection.execute(
                    """
                    UPDATE knowledge_entities
                    SET name = ?, sensitivity = ?, updated_at = ?, is_active = 1,
                        manual_source = CASE WHEN ? IS NULL THEN 1 ELSE manual_source END
                    WHERE id = ?
                    """,
                    (clean_name, resolved.value, _iso(now), source_memory_id, entity_id),
                )
            if source_memory_id is not None:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO knowledge_entity_sources(entity_id, memory_id)
                    VALUES (?, ?)
                    """,
                    (entity_id, source_memory_id),
                )
        return self.get_entity(entity_id, owner)

    def get_entity(self, entity_id: int, owner: str) -> KnowledgeEntity:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM knowledge_entities WHERE id = ? AND owner = ? COLLATE NOCASE",
                (int(entity_id), owner),
            ).fetchone()
        if row is None:
            raise LookupError("Entidade não encontrada.")
        return self._entity(row)

    def add_alias(
        self,
        *,
        owner: str,
        entity_id: int,
        alias: str,
        source_memory_id: int | None = None,
    ) -> None:
        entity = self.get_entity(entity_id, owner)
        if not entity.is_active:
            raise LookupError("A entidade está inativa.")
        clean = " ".join(str(alias or "").split()).strip(" .,-:;")
        normalized = normalize_knowledge_text(clean)
        if not normalized:
            raise ValueError("O alias precisa ter conteúdo.")
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO knowledge_aliases(
                    owner, entity_id, alias, normalized_alias, source_memory_id, is_active
                ) VALUES (?, ?, ?, ?, ?, 1)
                """,
                (owner, entity_id, clean, normalized, source_memory_id),
            )
            connection.execute(
                """
                UPDATE knowledge_aliases
                SET alias = ?, is_active = 1
                WHERE owner = ? COLLATE NOCASE
                  AND entity_id = ?
                  AND normalized_alias = ?
                """,
                (clean, owner, entity_id, normalized),
            )

    def resolve_entities(self, owner: str, query: str) -> tuple[KnowledgeEntity, ...]:
        normalized = normalize_knowledge_text(query)
        if not normalized:
            return ()
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT DISTINCT e.*
                FROM knowledge_entities e
                LEFT JOIN knowledge_aliases a
                  ON a.entity_id = e.id AND a.is_active = 1
                WHERE e.owner = ? COLLATE NOCASE
                  AND e.is_active = 1
                  AND (e.normalized_name = ? OR a.normalized_alias = ?)
                ORDER BY e.id ASC
                """,
                (owner, normalized, normalized),
            ).fetchall()
            if not rows:
                rows = connection.execute(
                    """
                    SELECT DISTINCT e.*
                    FROM knowledge_entities e
                    LEFT JOIN knowledge_aliases a
                      ON a.entity_id = e.id AND a.is_active = 1
                    WHERE e.owner = ? COLLATE NOCASE
                      AND e.is_active = 1
                      AND (
                        e.normalized_name LIKE ?
                        OR a.normalized_alias LIKE ?
                      )
                    ORDER BY LENGTH(e.normalized_name), e.id
                    LIMIT 10
                    """,
                    (owner, f"%{normalized}%", f"%{normalized}%"),
                ).fetchall()
        return tuple(self._entity(row) for row in rows)

    def list_entities(self, owner: str, *, limit: int = 50) -> tuple[KnowledgeEntity, ...]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM knowledge_entities
                WHERE owner = ? COLLATE NOCASE AND is_active = 1
                ORDER BY updated_at DESC, id DESC
                LIMIT ?
                """,
                (owner, max(1, min(int(limit), 200))),
            ).fetchall()
        return tuple(self._entity(row) for row in rows)

    def add_relation(
        self,
        *,
        owner: str,
        subject_id: int,
        predicate: str,
        object_id: int,
        sensitivity: MemorySensitivity = MemorySensitivity.NORMAL,
        confidence: float = 1.0,
        source_memory_id: int | None = None,
        valid_from: datetime | None = None,
        valid_until: datetime | None = None,
    ) -> KnowledgeRelation:
        self.get_entity(subject_id, owner)
        self.get_entity(object_id, owner)
        clean_predicate = normalize_knowledge_text(predicate).replace(" ", "_")
        if not clean_predicate:
            raise ValueError("A relação precisa ter um predicado.")
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM knowledge_relations
                WHERE owner = ? COLLATE NOCASE
                  AND subject_id = ? AND predicate = ? AND object_id = ?
                  AND COALESCE(source_memory_id, -1) = COALESCE(?, -1)
                ORDER BY is_active DESC, id ASC LIMIT 1
                """,
                (owner, subject_id, clean_predicate, object_id, source_memory_id),
            ).fetchone()
            if row is None:
                cursor = connection.execute(
                    """
                    INSERT INTO knowledge_relations(
                        owner, subject_id, predicate, object_id, sensitivity,
                        confidence, source_memory_id, valid_from, valid_until,
                        created_at, is_active
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                    """,
                    (
                        owner,
                        subject_id,
                        clean_predicate,
                        object_id,
                        sensitivity.value,
                        max(0.0, min(float(confidence), 1.0)),
                        source_memory_id,
                        _iso(valid_from),
                        _iso(valid_until),
                        _iso(_now()),
                    ),
                )
                relation_id = int(cursor.lastrowid)
            else:
                relation_id = int(row["id"])
                connection.execute(
                    "UPDATE knowledge_relations SET is_active = 1 WHERE id = ?",
                    (relation_id,),
                )
        return self.get_relation(relation_id, owner)

    def get_relation(self, relation_id: int, owner: str) -> KnowledgeRelation:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM knowledge_relations WHERE id = ? AND owner = ? COLLATE NOCASE",
                (int(relation_id), owner),
            ).fetchone()
        if row is None:
            raise LookupError("Relação não encontrada.")
        return self._relation(row)

    def relations(
        self,
        *,
        owner: str,
        entity_id: int,
        predicate: str | None = None,
        direction: str = "out",
    ) -> tuple[KnowledgeRelation, ...]:
        params: list[object] = [owner]
        side = "subject_id" if direction == "out" else "object_id"
        query = (
            "SELECT * FROM knowledge_relations "
            f"WHERE owner = ? COLLATE NOCASE AND is_active = 1 AND {side} = ?"
        )
        params.append(int(entity_id))
        if predicate:
            query += " AND predicate = ?"
            params.append(normalize_knowledge_text(predicate).replace(" ", "_"))
        query += " ORDER BY id ASC"
        with self.database.connect() as connection:
            rows = connection.execute(query, tuple(params)).fetchall()
        return tuple(self._relation(row) for row in rows)

    def add_fact(
        self,
        *,
        owner: str,
        entity_id: int,
        key: str,
        value: str,
        sensitivity: MemorySensitivity = MemorySensitivity.NORMAL,
        confidence: float = 1.0,
        source_memory_id: int | None = None,
        valid_from: datetime | None = None,
        valid_until: datetime | None = None,
    ) -> KnowledgeFact:
        self.get_entity(entity_id, owner)
        clean_key = normalize_knowledge_text(key).replace(" ", "_")
        clean_value = " ".join(str(value or "").split()).strip()
        normalized_value = normalize_knowledge_text(clean_value)
        if not clean_key or not normalized_value:
            raise ValueError("Fato inválido.")
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM knowledge_facts
                WHERE owner = ? COLLATE NOCASE AND entity_id = ? AND key = ?
                  AND normalized_value = ?
                  AND COALESCE(source_memory_id, -1) = COALESCE(?, -1)
                ORDER BY is_active DESC, id ASC LIMIT 1
                """,
                (owner, entity_id, clean_key, normalized_value, source_memory_id),
            ).fetchone()
            if row is None:
                cursor = connection.execute(
                    """
                    INSERT INTO knowledge_facts(
                        owner, entity_id, key, value, normalized_value,
                        sensitivity, confidence, source_memory_id,
                        valid_from, valid_until, created_at, is_active
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                    """,
                    (
                        owner,
                        entity_id,
                        clean_key,
                        clean_value,
                        normalized_value,
                        sensitivity.value,
                        max(0.0, min(float(confidence), 1.0)),
                        source_memory_id,
                        _iso(valid_from),
                        _iso(valid_until),
                        _iso(_now()),
                    ),
                )
                fact_id = int(cursor.lastrowid)
            else:
                fact_id = int(row["id"])
                connection.execute(
                    "UPDATE knowledge_facts SET is_active = 1 WHERE id = ?",
                    (fact_id,),
                )
        return self.get_fact(fact_id, owner)

    def get_fact(self, fact_id: int, owner: str) -> KnowledgeFact:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM knowledge_facts WHERE id = ? AND owner = ? COLLATE NOCASE",
                (int(fact_id), owner),
            ).fetchone()
        if row is None:
            raise LookupError("Fato não encontrado.")
        return self._fact(row)

    def facts(
        self,
        *,
        owner: str,
        entity_id: int,
        key: str | None = None,
    ) -> tuple[KnowledgeFact, ...]:
        params: list[object] = [owner, int(entity_id)]
        query = "SELECT * FROM knowledge_facts WHERE owner = ? COLLATE NOCASE AND entity_id = ? AND is_active = 1"
        if key:
            query += " AND key = ?"
            params.append(normalize_knowledge_text(key).replace(" ", "_"))
        query += " ORDER BY id ASC"
        with self.database.connect() as connection:
            rows = connection.execute(query, tuple(params)).fetchall()
        return tuple(self._fact(row) for row in rows)

    def deactivate_source(self, *, owner: str, memory_id: int) -> None:
        with self.database.connect() as connection:
            connection.execute(
                "UPDATE knowledge_relations SET is_active = 0 WHERE owner = ? COLLATE NOCASE AND source_memory_id = ?",
                (owner, int(memory_id)),
            )
            connection.execute(
                "UPDATE knowledge_facts SET is_active = 0 WHERE owner = ? COLLATE NOCASE AND source_memory_id = ?",
                (owner, int(memory_id)),
            )
            connection.execute(
                "UPDATE knowledge_aliases SET is_active = 0 WHERE owner = ? COLLATE NOCASE AND source_memory_id = ?",
                (owner, int(memory_id)),
            )
            entity_ids = [
                int(row["entity_id"])
                for row in connection.execute(
                    "SELECT entity_id FROM knowledge_entity_sources WHERE memory_id = ?",
                    (int(memory_id),),
                ).fetchall()
            ]
            connection.execute(
                "DELETE FROM knowledge_entity_sources WHERE memory_id = ?",
                (int(memory_id),),
            )
            for entity_id in entity_ids:
                source_count = int(
                    connection.execute(
                        "SELECT COUNT(*) AS total FROM knowledge_entity_sources WHERE entity_id = ?",
                        (entity_id,),
                    ).fetchone()["total"]
                )
                row = connection.execute(
                    "SELECT manual_source FROM knowledge_entities WHERE id = ?",
                    (entity_id,),
                ).fetchone()
                if row is not None and source_count == 0 and not bool(row["manual_source"]):
                    connection.execute(
                        "UPDATE knowledge_entities SET is_active = 0, updated_at = ? WHERE id = ?",
                        (_iso(_now()), entity_id),
                    )

    @staticmethod
    def _entity(row: sqlite3.Row) -> KnowledgeEntity:
        return KnowledgeEntity(
            id=int(row["id"]),
            owner=str(row["owner"]),
            name=str(row["name"]),
            normalized_name=str(row["normalized_name"]),
            kind=EntityKind(str(row["kind"])),
            sensitivity=MemorySensitivity(str(row["sensitivity"])),
            created_at=_dt(str(row["created_at"])) or _now(),
            updated_at=_dt(str(row["updated_at"])) or _now(),
            is_active=bool(row["is_active"]),
        )

    @staticmethod
    def _relation(row: sqlite3.Row) -> KnowledgeRelation:
        return KnowledgeRelation(
            id=int(row["id"]),
            owner=str(row["owner"]),
            subject_id=int(row["subject_id"]),
            predicate=str(row["predicate"]),
            object_id=int(row["object_id"]),
            sensitivity=MemorySensitivity(str(row["sensitivity"])),
            confidence=float(row["confidence"]),
            source_memory_id=int(row["source_memory_id"]) if row["source_memory_id"] is not None else None,
            valid_from=_dt(row["valid_from"]),
            valid_until=_dt(row["valid_until"]),
            created_at=_dt(str(row["created_at"])) or _now(),
            is_active=bool(row["is_active"]),
        )

    @staticmethod
    def _fact(row: sqlite3.Row) -> KnowledgeFact:
        return KnowledgeFact(
            id=int(row["id"]),
            owner=str(row["owner"]),
            entity_id=int(row["entity_id"]),
            key=str(row["key"]),
            value=str(row["value"]),
            normalized_value=str(row["normalized_value"]),
            sensitivity=MemorySensitivity(str(row["sensitivity"])),
            confidence=float(row["confidence"]),
            source_memory_id=int(row["source_memory_id"]) if row["source_memory_id"] is not None else None,
            valid_from=_dt(row["valid_from"]),
            valid_until=_dt(row["valid_until"]),
            created_at=_dt(str(row["created_at"])) or _now(),
            is_active=bool(row["is_active"]),
        )
