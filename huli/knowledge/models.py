"""Modelos imutáveis do Personal Knowledge Graph da Huli."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from huli.memory import MemorySensitivity


class EntityKind(StrEnum):
    PERSON = "person"
    PROJECT = "project"
    COMPANY = "company"
    CLIENT = "client"
    SYSTEM = "system"
    EQUIPMENT = "equipment"
    PLACE = "place"
    CONCEPT = "concept"


@dataclass(frozen=True, slots=True)
class KnowledgeEntity:
    id: int
    owner: str
    name: str
    normalized_name: str
    kind: EntityKind
    sensitivity: MemorySensitivity
    created_at: datetime
    updated_at: datetime
    is_active: bool


@dataclass(frozen=True, slots=True)
class KnowledgeRelation:
    id: int
    owner: str
    subject_id: int
    predicate: str
    object_id: int
    sensitivity: MemorySensitivity
    confidence: float
    source_memory_id: int | None
    valid_from: datetime | None
    valid_until: datetime | None
    created_at: datetime
    is_active: bool


@dataclass(frozen=True, slots=True)
class KnowledgeFact:
    id: int
    owner: str
    entity_id: int
    key: str
    value: str
    normalized_value: str
    sensitivity: MemorySensitivity
    confidence: float
    source_memory_id: int | None
    valid_from: datetime | None
    valid_until: datetime | None
    created_at: datetime
    is_active: bool
