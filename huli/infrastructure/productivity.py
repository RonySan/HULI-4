"""Repositórios locais de tarefas e compromissos da Huli."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import unicodedata

from huli.infrastructure.database import SQLiteDatabase


def _description_key(text: str) -> str:
    return " ".join("".join(char for char in unicodedata.normalize("NFKD", text.casefold()) if not unicodedata.combining(char)).split())


@dataclass(frozen=True, slots=True)
class TaskRecord:
    id: int
    title: str
    status: str
    priority: str
    project: str | None
    due_at: str | None
    created_at: str
    completed_at: str | None


@dataclass(frozen=True, slots=True)
class AppointmentRecord:
    id: int
    title: str
    start_at: str
    end_at: str | None
    status: str
    project: str | None
    created_at: str
    cancelled_at: str | None
    source: str = "local"
    external_id: str | None = None
    calendar_name: str | None = None


class TaskRepository:
    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database

    def create(self, title: str, *, priority: str = "normal", project: str | None = None, due_at: datetime | None = None) -> TaskRecord:
        normalized_title = " ".join(str(title or "").split()).strip()
        if not normalized_title:
            raise ValueError("A tarefa precisa ter um título.")
        normalized_priority = priority if priority in {"baixa", "normal", "alta"} else "normal"
        project_value = " ".join(project.split()).strip() if project else None
        due_value = due_at.isoformat() if due_at else None
        with self.database.connect() as connection:
            cursor = connection.execute(
                "INSERT INTO tasks(title, status, priority, project, due_at) VALUES (?, 'pending', ?, ?, ?)",
                (normalized_title, normalized_priority, project_value, due_value),
            )
            row = connection.execute("SELECT * FROM tasks WHERE id = ?", (int(cursor.lastrowid),)).fetchone()
        return self._from_row(row)

    def list_pending(self, *, project: str | None = None, limit: int = 20) -> tuple[TaskRecord, ...]:
        safe_limit = max(1, min(int(limit), 200))
        query = "SELECT * FROM tasks WHERE status = 'pending'"
        args: list[object] = []
        if project:
            query += " AND project = ? COLLATE NOCASE"
            args.append(project.strip())
        query += " ORDER BY CASE priority WHEN 'alta' THEN 0 WHEN 'normal' THEN 1 ELSE 2 END, id ASC LIMIT ?"
        args.append(safe_limit)
        with self.database.connect() as connection:
            rows = connection.execute(query, tuple(args)).fetchall()
        return tuple(self._from_row(row) for row in rows)

    def complete(self, identifier: str, *, project: str | None = None) -> TaskRecord | None:
        normalized = " ".join(str(identifier or "").split()).strip()
        if not normalized:
            return None
        with self.database.connect() as connection:
            if normalized.isdigit():
                row = connection.execute("SELECT * FROM tasks WHERE id = ? AND status = 'pending'", (int(normalized),)).fetchone()
            else:
                candidates = connection.execute("SELECT * FROM tasks WHERE status = 'pending' ORDER BY id ASC").fetchall()
                matches = [item for item in candidates if _description_key(normalized) in _description_key(str(item["title"]))
                           and (not project or _description_key(str(item["project"] or "")) == _description_key(project))]
                if len(matches) > 1:
                    raise ValueError("Encontrei mais de uma tarefa. Informe o número: " + ", ".join(f"#{item['id']} {item['title']}" for item in matches[:5]))
                row = matches[0] if matches else None
            if row is None:
                return None
            connection.execute("UPDATE tasks SET status = 'completed', completed_at = CURRENT_TIMESTAMP WHERE id = ?", (int(row["id"]),))
            updated = connection.execute("SELECT * FROM tasks WHERE id = ?", (int(row["id"]),)).fetchone()
        return self._from_row(updated)

    def count_pending(self, project: str | None = None) -> int:
        query = "SELECT COUNT(*) AS total FROM tasks WHERE status = 'pending'"
        args: list[object] = []
        if project:
            query += " AND project = ? COLLATE NOCASE"
            args.append(project.strip())
        with self.database.connect() as connection:
            row = connection.execute(query, tuple(args)).fetchone()
        return int(row["total"]) if row else 0

    @staticmethod
    def _from_row(row) -> TaskRecord:
        if row is None:
            raise RuntimeError("Registro de tarefa não encontrado.")
        return TaskRecord(
            id=int(row["id"]), title=str(row["title"]), status=str(row["status"]), priority=str(row["priority"]),
            project=str(row["project"]) if row["project"] is not None else None,
            due_at=str(row["due_at"]) if row["due_at"] is not None else None,
            created_at=str(row["created_at"]), completed_at=str(row["completed_at"]) if row["completed_at"] is not None else None,
        )


class AppointmentRepository:
    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database

    def create(self, title: str, start_at: datetime, *, end_at: datetime | None = None, project: str | None = None) -> AppointmentRecord:
        normalized_title = " ".join(str(title or "").split()).strip()
        if not normalized_title:
            raise ValueError("O compromisso precisa ter um título.")
        project_value = " ".join(project.split()).strip() if project else None
        with self.database.connect() as connection:
            cursor = connection.execute(
                "INSERT INTO appointments(title, start_at, end_at, status, project) VALUES (?, ?, ?, 'scheduled', ?)",
                (normalized_title, start_at.isoformat(), end_at.isoformat() if end_at else None, project_value),
            )
            row = connection.execute("SELECT * FROM appointments WHERE id = ?", (int(cursor.lastrowid),)).fetchone()
        return self._from_row(row)

    def upsert_external(
        self,
        *,
        source: str,
        external_id: str,
        title: str,
        start_at: datetime,
        end_at: datetime | None,
        calendar_name: str,
    ) -> str:
        source_value = " ".join(source.split()).casefold()
        remote_value = " ".join(external_id.split())
        title_value = " ".join(title.split()) or "(sem título)"
        if not source_value or not remote_value:
            raise ValueError("O compromisso externo precisa de origem e identificador.")
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM appointments WHERE source = ? AND external_id = ?",
                (source_value, remote_value),
            ).fetchone()
            values = (
                title_value,
                start_at.isoformat(),
                end_at.isoformat() if end_at else None,
                calendar_name,
            )
            if row is None:
                connection.execute(
                    """
                    INSERT INTO appointments(
                        title, start_at, end_at, status, project, source, external_id, calendar_name
                    ) VALUES (?, ?, ?, 'scheduled', NULL, ?, ?, ?)
                    """,
                    (*values[:3], source_value, remote_value, values[3]),
                )
                return "created"
            changed = any(
                str(row[key] or "") != str(value or "")
                for key, value in zip(("title", "start_at", "end_at", "calendar_name"), values)
            ) or str(row["status"]) != "scheduled"
            if changed:
                connection.execute(
                    """
                    UPDATE appointments
                    SET title = ?, start_at = ?, end_at = ?, status = 'scheduled',
                        cancelled_at = NULL, calendar_name = ?
                    WHERE id = ?
                    """,
                    (*values, int(row["id"])),
                )
                return "updated"
        return "unchanged"

    def cancel_external(self, source: str, external_id: str) -> bool:
        with self.database.connect() as connection:
            cursor = connection.execute(
                """
                UPDATE appointments
                SET status = 'cancelled', cancelled_at = CURRENT_TIMESTAMP
                WHERE source = ? AND external_id = ? AND status = 'scheduled'
                """,
                (source.casefold(), external_id),
            )
        return cursor.rowcount > 0

    def list_between(self, start_at: datetime, end_at: datetime, *, limit: int = 50) -> tuple[AppointmentRecord, ...]:
        safe_limit = max(1, min(int(limit), 200))
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM appointments WHERE status = 'scheduled' AND start_at >= ? AND start_at < ? ORDER BY start_at ASC LIMIT ?",
                (start_at.isoformat(), end_at.isoformat(), safe_limit),
            ).fetchall()
        return tuple(self._from_row(row) for row in rows)

    def list_upcoming(self, after: datetime, *, limit: int = 20) -> tuple[AppointmentRecord, ...]:
        safe_limit = max(1, min(int(limit), 200))
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM appointments WHERE status = 'scheduled' AND start_at >= ? ORDER BY start_at ASC LIMIT ?",
                (after.isoformat(), safe_limit),
            ).fetchall()
        return tuple(self._from_row(row) for row in rows)

    def cancel(self, identifier: str) -> AppointmentRecord | None:
        normalized = " ".join(str(identifier or "").split()).strip()
        if not normalized:
            return None
        with self.database.connect() as connection:
            if normalized.isdigit():
                row = connection.execute("SELECT * FROM appointments WHERE id = ? AND status = 'scheduled' AND source = 'local'", (int(normalized),)).fetchone()
            else:
                candidates = connection.execute("SELECT * FROM appointments WHERE status = 'scheduled' AND source = 'local' ORDER BY start_at ASC").fetchall()
                matches = [item for item in candidates if _description_key(normalized) in _description_key(str(item["title"]))]
                if len(matches) > 1:
                    raise ValueError("Encontrei mais de um compromisso. Informe o número: " + ", ".join(f"#{item['id']} {item['title']}" for item in matches[:5]))
                row = matches[0] if matches else None
            if row is None:
                return None
            connection.execute("UPDATE appointments SET status = 'cancelled', cancelled_at = CURRENT_TIMESTAMP WHERE id = ?", (int(row["id"]),))
            updated = connection.execute("SELECT * FROM appointments WHERE id = ?", (int(row["id"]),)).fetchone()
        return self._from_row(updated)

    def complete(self, identifier: str) -> AppointmentRecord | None:
        normalized = " ".join(str(identifier or "").split()).strip()
        if not normalized:
            return None
        with self.database.connect() as connection:
            if normalized.isdigit():
                row = connection.execute(
                    "SELECT * FROM appointments WHERE id = ? AND status = 'scheduled' AND source = 'local'",
                    (int(normalized),),
                ).fetchone()
            else:
                candidates = connection.execute(
                    "SELECT * FROM appointments WHERE status = 'scheduled' AND source = 'local' ORDER BY start_at ASC"
                ).fetchall()
                matches = [
                    item
                    for item in candidates
                    if _description_key(normalized)
                    in _description_key(str(item["title"]))
                ]
                if len(matches) > 1:
                    raise ValueError(
                        "Encontrei mais de um compromisso. Informe o número: "
                        + ", ".join(
                            f"#{item['id']} {item['title']}" for item in matches[:5]
                        )
                    )
                row = matches[0] if matches else None
            if row is None:
                return None
            connection.execute(
                "UPDATE appointments SET status = 'completed' WHERE id = ?",
                (int(row["id"]),),
            )
            updated = connection.execute(
                "SELECT * FROM appointments WHERE id = ?",
                (int(row["id"]),),
            ).fetchone()
        return self._from_row(updated)

    @staticmethod
    def _from_row(row) -> AppointmentRecord:
        if row is None:
            raise RuntimeError("Registro de compromisso não encontrado.")
        return AppointmentRecord(
            id=int(row["id"]), title=str(row["title"]), start_at=str(row["start_at"]),
            end_at=str(row["end_at"]) if row["end_at"] is not None else None,
            status=str(row["status"]), project=str(row["project"]) if row["project"] is not None else None,
            created_at=str(row["created_at"]), cancelled_at=str(row["cancelled_at"]) if row["cancelled_at"] is not None else None,
            source=str(row["source"]) if "source" in row.keys() else "local",
            external_id=str(row["external_id"]) if "external_id" in row.keys() and row["external_id"] is not None else None,
            calendar_name=str(row["calendar_name"]) if "calendar_name" in row.keys() and row["calendar_name"] is not None else None,
        )
