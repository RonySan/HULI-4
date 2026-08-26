"""Contexto curto e efêmero das sessões da Huli."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock


@dataclass(frozen=True, slots=True)
class ContextTurn:
    text: str
    intent: str
    topic: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True, slots=True)
class ContextSnapshot:
    session_id: str
    last_intent: str | None
    last_topic: str | None
    active_project: str | None
    turn_count: int


class ContextEngine:
    """Mantém apenas o contexto da sessão atual, sem virar memória de longo prazo."""

    def __init__(self, max_turns: int = 20) -> None:
        self.max_turns = max(1, int(max_turns))
        self._turns: dict[str, deque[ContextTurn]] = {}
        self._active_projects: dict[str, str] = {}
        self._lock = RLock()

    def observe(
        self,
        session_id: str,
        text: str,
        intent: str,
        *,
        topic: str | None = None,
    ) -> ContextSnapshot:
        session = self._normalize_session_id(session_id)
        with self._lock:
            turns = self._turns.setdefault(session, deque(maxlen=self.max_turns))
            turns.append(ContextTurn(text=text.strip(), intent=intent, topic=topic))
            return self._snapshot_unlocked(session)

    def set_active_project(self, session_id: str, project: str) -> ContextSnapshot:
        session = self._normalize_session_id(session_id)
        normalized = " ".join(str(project or "").split()).strip()
        if not normalized:
            raise ValueError("O nome do projeto não pode estar vazio.")
        if len(normalized) > 120:
            raise ValueError("O nome do projeto pode ter no máximo 120 caracteres.")
        with self._lock:
            self._active_projects[session] = normalized
            return self._snapshot_unlocked(session)

    def clear_active_project(self, session_id: str) -> ContextSnapshot:
        session = self._normalize_session_id(session_id)
        with self._lock:
            self._active_projects.pop(session, None)
            return self._snapshot_unlocked(session)

    def snapshot(self, session_id: str) -> ContextSnapshot:
        session = self._normalize_session_id(session_id)
        with self._lock:
            return self._snapshot_unlocked(session)

    def recent_turns(self, session_id: str, limit: int = 10) -> tuple[ContextTurn, ...]:
        session = self._normalize_session_id(session_id)
        safe_limit = max(1, min(int(limit), self.max_turns))
        with self._lock:
            turns = tuple(self._turns.get(session, ()))
        return turns[-safe_limit:]

    def clear(self, session_id: str) -> None:
        session = self._normalize_session_id(session_id)
        with self._lock:
            self._turns.pop(session, None)
            self._active_projects.pop(session, None)

    def _snapshot_unlocked(self, session_id: str) -> ContextSnapshot:
        turns = self._turns.get(session_id)
        last = turns[-1] if turns else None
        return ContextSnapshot(
            session_id=session_id,
            last_intent=last.intent if last else None,
            last_topic=last.topic if last else None,
            active_project=self._active_projects.get(session_id),
            turn_count=len(turns) if turns else 0,
        )

    @staticmethod
    def _normalize_session_id(session_id: str) -> str:
        normalized = str(session_id or "default").strip() or "default"
        if len(normalized) > 128:
            raise ValueError("session_id pode ter no máximo 128 caracteres.")
        return normalized
