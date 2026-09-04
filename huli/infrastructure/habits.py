"""Persistencia local dos habitos pessoais."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import unicodedata

from huli.infrastructure.database import SQLiteDatabase


def _key(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", str(value or "").casefold())
    return " ".join(
        "".join(char for char in decomposed if not unicodedata.combining(char)).split()
    )


@dataclass(frozen=True, slots=True)
class HabitRecord:
    id: int
    owner: str
    name: str
    normalized_name: str
    created_at: str


class HabitRepository:
    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database

    def create(self, owner: str, name: str) -> HabitRecord:
        clean_owner = " ".join(str(owner or "").split()).strip()
        clean_name = " ".join(str(name or "").split()).strip(" .,-")
        normalized = _key(clean_name)
        if not clean_owner:
            raise ValueError("O hábito precisa de um proprietário.")
        if not normalized:
            raise ValueError("Informe o nome do hábito.")
        with self.database.connect() as connection:
            existing = connection.execute(
                "SELECT * FROM habits WHERE owner = ? COLLATE NOCASE AND normalized_name = ? AND is_active = 1",
                (clean_owner, normalized),
            ).fetchone()
            if existing is not None:
                raise ValueError(f"O hábito '{existing['name']}' já existe.")
            cursor = connection.execute(
                "INSERT INTO habits(owner, name, normalized_name) VALUES (?, ?, ?)",
                (clean_owner, clean_name, normalized),
            )
            row = connection.execute(
                "SELECT * FROM habits WHERE id = ?", (int(cursor.lastrowid),)
            ).fetchone()
        return self._from_row(row)

    def list_active(self, owner: str) -> tuple[HabitRecord, ...]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM habits WHERE owner = ? COLLATE NOCASE AND is_active = 1 ORDER BY id",
                (owner.strip(),),
            ).fetchall()
        return tuple(self._from_row(row) for row in rows)

    def resolve(self, owner: str, identifier: str) -> HabitRecord | None:
        value = " ".join(str(identifier or "").split()).strip(" #.,")
        if not value:
            return None
        with self.database.connect() as connection:
            if value.isdigit():
                row = connection.execute(
                    "SELECT * FROM habits WHERE id = ? AND owner = ? COLLATE NOCASE AND is_active = 1",
                    (int(value), owner.strip()),
                ).fetchone()
                return self._from_row(row) if row is not None else None
            rows = connection.execute(
                "SELECT * FROM habits WHERE owner = ? COLLATE NOCASE AND is_active = 1 ORDER BY id",
                (owner.strip(),),
            ).fetchall()
        target = _key(value)
        matches = [row for row in rows if target in str(row["normalized_name"])]
        if len(matches) > 1:
            raise ValueError(
                "Encontrei mais de um hábito. Informe o número: "
                + ", ".join(f"#{row['id']} {row['name']}" for row in matches[:5])
            )
        return self._from_row(matches[0]) if matches else None

    def mark_done(self, habit_id: int, day: date) -> bool:
        with self.database.connect() as connection:
            cursor = connection.execute(
                "INSERT OR IGNORE INTO habit_completions(habit_id, completion_date) VALUES (?, ?)",
                (int(habit_id), day.isoformat()),
            )
        return cursor.rowcount > 0

    def completion_dates(self, habit_id: int, *, since: date | None = None) -> frozenset[date]:
        query = "SELECT completion_date FROM habit_completions WHERE habit_id = ?"
        args: list[object] = [int(habit_id)]
        if since is not None:
            query += " AND completion_date >= ?"
            args.append(since.isoformat())
        with self.database.connect() as connection:
            rows = connection.execute(query, tuple(args)).fetchall()
        return frozenset(date.fromisoformat(str(row["completion_date"])) for row in rows)

    @staticmethod
    def _from_row(row) -> HabitRecord:
        return HabitRecord(
            id=int(row["id"]),
            owner=str(row["owner"]),
            name=str(row["name"]),
            normalized_name=str(row["normalized_name"]),
            created_at=str(row["created_at"]),
        )
