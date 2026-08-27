"""Serviço do diário pessoal, sem aprendizado automático."""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from huli.core.events import EventBus
from huli.journal.models import JournalEntry
from huli.journal.normalization import build_search_text
from huli.journal.policy import JournalPolicy
from huli.journal.repository import JournalRepository


class JournalService:
    def __init__(
        self,
        repository: JournalRepository,
        policy: JournalPolicy,
        events: EventBus,
        timezone_name: str,
    ) -> None:
        self.repository = repository
        self.policy = policy
        self.events = events
        self.timezone = ZoneInfo(timezone_name)

    def today(self) -> date:
        return datetime.now(self.timezone).date()

    def create(
        self,
        *,
        owner: str,
        content: str,
        entry_date: date | None = None,
        mood: str | None = None,
        tags: tuple[str, ...] = (),
    ) -> JournalEntry:
        resolved_owner = self._validate_owner(owner)
        clean_content, sensitivity = self.policy.validate_content(content)
        clean_mood = self.policy.clean_mood(mood)
        clean_tags = self.policy.clean_tags(tags)
        record = self.repository.create(
            owner=resolved_owner,
            content=clean_content,
            search_text=build_search_text(
                clean_content,
                mood=clean_mood,
                tags=clean_tags,
            ),
            entry_date=entry_date or self.today(),
            mood=clean_mood,
            tags=clean_tags,
            sensitivity=sensitivity,
        )
        self.events.publish(
            "journal.entry.created",
            {
                "entry_id": record.id,
                "owner": record.owner,
                "entry_date": record.entry_date.isoformat(),
                "sensitivity": record.sensitivity.value,
                "tag_count": len(record.tags),
            },
        )
        return record

    def entries_on(self, *, owner: str, entry_date: date) -> tuple[JournalEntry, ...]:
        resolved_owner = self._validate_owner(owner)
        records = self.repository.list_entries(
            resolved_owner,
            start_date=entry_date,
            end_date=entry_date,
            limit=100,
        )
        self._publish_read(resolved_owner, records, operation="date")
        return records

    def recent(self, *, owner: str, limit: int = 10) -> tuple[JournalEntry, ...]:
        resolved_owner = self._validate_owner(owner)
        records = self.repository.list_entries(resolved_owner, limit=limit)
        self._publish_read(resolved_owner, records, operation="recent")
        return records

    def search(
        self,
        *,
        owner: str,
        query: str,
        limit: int = 20,
    ) -> tuple[JournalEntry, ...]:
        resolved_owner = self._validate_owner(owner)
        records = self.repository.search(resolved_owner, query, limit=limit)
        self._publish_read(resolved_owner, records, operation="search")
        return records

    def trash(self, *, owner: str, limit: int = 20) -> tuple[JournalEntry, ...]:
        resolved_owner = self._validate_owner(owner)
        records = self.repository.list_deleted(resolved_owner, limit=limit)
        self._publish_read(resolved_owner, records, operation="trash")
        return records

    def update(
        self,
        *,
        owner: str,
        entry_id: int,
        content: str,
        mood: str | None = None,
        tags: tuple[str, ...] = (),
        preserve_mood: bool = True,
        preserve_tags: bool = True,
    ) -> JournalEntry:
        resolved_owner = self._validate_owner(owner)
        current = self.repository.get(entry_id, resolved_owner)
        clean_content, sensitivity = self.policy.validate_content(content)
        clean_mood = (
            current.mood if preserve_mood else self.policy.clean_mood(mood)
        )
        clean_tags = (
            current.tags if preserve_tags else self.policy.clean_tags(tags)
        )
        record = self.repository.update(
            entry_id=entry_id,
            owner=resolved_owner,
            content=clean_content,
            search_text=build_search_text(
                clean_content,
                mood=clean_mood,
                tags=clean_tags,
            ),
            mood=clean_mood,
            tags=clean_tags,
            sensitivity=sensitivity,
        )
        self.events.publish(
            "journal.entry.updated",
            {
                "entry_id": record.id,
                "owner": record.owner,
                "entry_date": record.entry_date.isoformat(),
                "sensitivity": record.sensitivity.value,
                "tag_count": len(record.tags),
            },
        )
        return record

    def delete(self, *, owner: str, entry_id: int) -> JournalEntry:
        resolved_owner = self._validate_owner(owner)
        record = self.repository.delete(entry_id, resolved_owner)
        self.events.publish(
            "journal.entry.deleted",
            {
                "entry_id": record.id,
                "owner": record.owner,
                "entry_date": record.entry_date.isoformat(),
            },
        )
        return record

    def restore(self, *, owner: str, entry_id: int) -> JournalEntry:
        resolved_owner = self._validate_owner(owner)
        record = self.repository.restore(entry_id, resolved_owner)
        self.events.publish(
            "journal.entry.restored",
            {
                "entry_id": record.id,
                "owner": record.owner,
                "entry_date": record.entry_date.isoformat(),
            },
        )
        return record

    def _publish_read(
        self,
        owner: str,
        records: tuple[JournalEntry, ...],
        *,
        operation: str,
    ) -> None:
        self.events.publish(
            "journal.entries.read",
            {
                "owner": owner,
                "operation": operation,
                "entry_ids": [record.id for record in records],
                "count": len(records),
            },
        )

    @staticmethod
    def _validate_owner(owner: str) -> str:
        value = " ".join(str(owner or "").split()).strip()
        if not value:
            raise ValueError("O diário exige um proprietário autenticado.")
        return value


__all__ = ["JournalService"]
