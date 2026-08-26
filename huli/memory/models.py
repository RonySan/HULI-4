"""Modelos imutáveis da Memory Engine 4.0."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class MemoryKind(StrEnum):
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PERSON = "person"
    PROJECT = "project"
    PREFERENCE = "preference"
    TEMPORAL = "temporal"


class MemorySensitivity(StrEnum):
    NORMAL = "normal"
    SENSITIVE = "sensitive"
    SECRET = "secret"


class MemorySource(StrEnum):
    EXPLICIT = "explicit"
    AUTOMATIC = "automatic"
    IMPORTED = "imported"
    SYSTEM = "system"


@dataclass(frozen=True, slots=True)
class MemoryRecord:
    id: int
    owner: str
    kind: MemoryKind
    content: str
    normalized_content: str
    subject: str | None
    project: str | None
    sensitivity: MemorySensitivity
    source: MemorySource
    confidence: float
    occurred_at: datetime | None
    valid_until: datetime | None
    created_at: datetime
    updated_at: datetime
    last_accessed_at: datetime | None
    access_count: int
    is_active: bool
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class MemoryCandidate:
    owner: str
    content: str
    kind: MemoryKind = MemoryKind.SEMANTIC
    subject: str | None = None
    project: str | None = None
    confidence: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
