"""Repositórios e assinantes de persistência da fundação."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json

from huli.core.events import Event, EventBus
from huli.infrastructure.database import SQLiteDatabase


@dataclass(frozen=True, slots=True)
class Interaction:
    request_id: str
    user_text: str
    response_text: str
    handled_by: str
    ok: bool


class EventRepository:
    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database

    def add(self, event: Event) -> None:
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO events(event_id, name, payload_json, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.name,
                    json.dumps(event.payload, ensure_ascii=False, sort_keys=True),
                    event.created_at.isoformat(),
                ),
            )

    def count(self) -> int:
        with self.database.connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS total FROM events").fetchone()
            return int(row["total"]) if row else 0


class InteractionRepository:
    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database

    def add(self, interaction: Interaction) -> None:
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO interactions(
                    request_id, user_text, response_text, handled_by, ok, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    interaction.request_id,
                    interaction.user_text,
                    interaction.response_text,
                    interaction.handled_by,
                    1 if interaction.ok else 0,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

    def latest(self, limit: int = 20) -> tuple[Interaction, ...]:
        safe_limit = max(1, min(int(limit), 200))
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT request_id, user_text, response_text, handled_by, ok
                FROM interactions
                ORDER BY id DESC
                LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()
        return tuple(
            Interaction(
                request_id=str(row["request_id"]),
                user_text=str(row["user_text"]),
                response_text=str(row["response_text"]),
                handled_by=str(row["handled_by"]),
                ok=bool(row["ok"]),
            )
            for row in rows
        )


class RuntimeRecorder:
    """Observa eventos do Kernel e os grava sem acoplá-lo ao SQLite."""

    def __init__(
        self,
        event_bus: EventBus,
        event_repository: EventRepository,
        interaction_repository: InteractionRepository,
    ) -> None:
        self._event_repository = event_repository
        self._interaction_repository = interaction_repository
        self._pending: dict[str, str] = {}
        event_bus.subscribe("kernel.request.received", self._on_request)
        event_bus.subscribe("kernel.response.created", self._on_response)

    def _on_request(self, event: Event) -> None:
        self._event_repository.add(event)
        request_id = str(event.payload.get("request_id", ""))
        text = str(event.payload.get("text", ""))
        if request_id:
            self._pending[request_id] = text

    def _on_response(self, event: Event) -> None:
        self._event_repository.add(event)
        request_id = str(event.payload.get("request_id", ""))
        user_text = self._pending.pop(request_id, "")
        if not request_id:
            return
        self._interaction_repository.add(
            Interaction(
                request_id=request_id,
                user_text=user_text,
                response_text=str(event.payload.get("text", "")),
                handled_by=str(event.payload.get("handled_by", "unknown")),
                ok=bool(event.payload.get("ok", False)),
            )
        )
