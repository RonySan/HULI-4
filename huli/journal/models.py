"""Modelos imutáveis do diário pessoal da Huli."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum


class JournalSensitivity(StrEnum):
    """Classificação mínima usada sem expor o conteúdo da entrada."""

    NORMAL = "normal"
    SENSITIVE = "sensitive"


@dataclass(frozen=True, slots=True)
class JournalEntry:
    id: int
    owner: str
    content: str
    search_text: str
    entry_date: date
    mood: str | None
    tags: tuple[str, ...]
    sensitivity: JournalSensitivity
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    is_active: bool


__all__ = ["JournalEntry", "JournalSensitivity"]
