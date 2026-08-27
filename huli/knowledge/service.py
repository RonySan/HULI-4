"""Serviço do Personal Knowledge Graph e sincronização com a Memory Engine."""

from __future__ import annotations

from dataclasses import dataclass
import re

from huli.core import Event, EventBus
from huli.knowledge.models import EntityKind, KnowledgeEntity, KnowledgeFact, KnowledgeRelation
from huli.knowledge.normalization import normalize_knowledge_text
from huli.knowledge.repository import KnowledgeRepository
from huli.memory import MemoryKind, MemoryRecord, MemoryRepository, MemorySensitivity


@dataclass(frozen=True, slots=True)
class KnowledgeSnapshot:
    entity: KnowledgeEntity
    outgoing: tuple[tuple[KnowledgeRelation, KnowledgeEntity], ...]
    incoming: tuple[tuple[KnowledgeRelation, KnowledgeEntity], ...]
    facts: tuple[KnowledgeFact, ...]


class KnowledgeService:
    def __init__(self, repository: KnowledgeRepository, event_bus: EventBus) -> None:
        self.repository = repository
        self.events = event_bus

    def ensure_entity(
        self,
        *,
        owner: str,
        name: str,
        kind: EntityKind = EntityKind.CONCEPT,
        sensitivity: MemorySensitivity = MemorySensitivity.NORMAL,
        source_memory_id: int | None = None,
        aliases: tuple[str, ...] = (),
    ) -> KnowledgeEntity:
        entity = self.repository.upsert_entity(
            owner=owner,
            name=name,
            kind=kind,
            sensitivity=sensitivity,
            source_memory_id=source_memory_id,
        )
        for alias in aliases:
            self.repository.add_alias(
                owner=owner,
                entity_id=entity.id,
                alias=alias,
                source_memory_id=source_memory_id,
            )
        self.events.publish(
            "knowledge.entity.upserted",
            {
                "owner": owner,
                "entity_id": entity.id,
                "name": entity.name,
                "kind": entity.kind.value,
                "source_memory_id": source_memory_id,
            },
        )
        return entity

    def add_relation(
        self,
        *,
        owner: str,
        subject: KnowledgeEntity,
        predicate: str,
        object_: KnowledgeEntity,
        sensitivity: MemorySensitivity = MemorySensitivity.NORMAL,
        confidence: float = 1.0,
        source_memory_id: int | None = None,
    ) -> KnowledgeRelation:
        relation = self.repository.add_relation(
            owner=owner,
            subject_id=subject.id,
            predicate=predicate,
            object_id=object_.id,
            sensitivity=sensitivity,
            confidence=confidence,
            source_memory_id=source_memory_id,
        )
        self.events.publish(
            "knowledge.relation.upserted",
            {
                "owner": owner,
                "relation_id": relation.id,
                "subject_id": subject.id,
                "predicate": relation.predicate,
                "object_id": object_.id,
                "source_memory_id": source_memory_id,
            },
        )
        return relation

    def add_fact(
        self,
        *,
        owner: str,
        entity: KnowledgeEntity,
        key: str,
        value: str,
        sensitivity: MemorySensitivity = MemorySensitivity.NORMAL,
        confidence: float = 1.0,
        source_memory_id: int | None = None,
    ) -> KnowledgeFact:
        fact = self.repository.add_fact(
            owner=owner,
            entity_id=entity.id,
            key=key,
            value=value,
            sensitivity=sensitivity,
            confidence=confidence,
            source_memory_id=source_memory_id,
        )
        self.events.publish(
            "knowledge.fact.upserted",
            {
                "owner": owner,
                "fact_id": fact.id,
                "entity_id": entity.id,
                "key": fact.key,
                "source_memory_id": source_memory_id,
            },
        )
        return fact

    def resolve(self, *, owner: str, query: str) -> KnowledgeEntity:
        entities = self.repository.resolve_entities(owner, query)
        if not entities:
            raise LookupError("Não encontrei essa entidade no conhecimento registrado.")
        if len(entities) > 1:
            names = ", ".join(f"{item.name} [{item.kind.value}]" for item in entities[:5])
            raise LookupError(f"A referência é ambígua: {names}.")
        return entities[0]

    def describe(self, *, owner: str, query: str) -> KnowledgeSnapshot:
        entity = self.resolve(owner=owner, query=query)
        outgoing = tuple(
            (relation, self.repository.get_entity(relation.object_id, owner))
            for relation in self.repository.relations(
                owner=owner,
                entity_id=entity.id,
                direction="out",
            )
        )
        incoming = tuple(
            (relation, self.repository.get_entity(relation.subject_id, owner))
            for relation in self.repository.relations(
                owner=owner,
                entity_id=entity.id,
                direction="in",
            )
        )
        facts = self.repository.facts(owner=owner, entity_id=entity.id)
        self.events.publish(
            "knowledge.queried",
            {"owner": owner, "entity_id": entity.id, "query": query},
        )
        return KnowledgeSnapshot(entity, outgoing, incoming, facts)

    def related(
        self,
        *,
        owner: str,
        subject_query: str,
        predicate: str,
    ) -> tuple[KnowledgeEntity, ...]:
        subject = self.resolve(owner=owner, query=subject_query)
        relations = self.repository.relations(
            owner=owner,
            entity_id=subject.id,
            predicate=predicate,
            direction="out",
        )
        seen: set[int] = set()
        result: list[KnowledgeEntity] = []
        for relation in relations:
            if relation.object_id in seen:
                continue
            seen.add(relation.object_id)
            result.append(self.repository.get_entity(relation.object_id, owner))
        self.events.publish(
            "knowledge.relation.queried",
            {
                "owner": owner,
                "subject_id": subject.id,
                "predicate": normalize_knowledge_text(predicate).replace(" ", "_"),
                "count": len(result),
            },
        )
        return tuple(result)


class MemoryKnowledgeSynchronizer:
    """Extrai somente relações/fatos suportados por padrões explícitos de memória."""

    _RELATION_PATTERNS = (
        (
            re.compile(
                r"^(?:o\s+projeto\s+)?(?P<subject>.+?)\s+(?:e|é)\s+desenvolvid[oa]\s+(?:por|pela|pelo)\s+(?P<object>.+)$",
                re.IGNORECASE,
            ),
            "desenvolvido_por",
        ),
        (
            re.compile(
                r"^(?:o\s+projeto\s+)?(?P<subject>.+?)\s+(?:esta|está)\s+hospedad[oa]\s+(?:em|no|na)\s+(?P<object>.+)$",
                re.IGNORECASE,
            ),
            "hospedado_em",
        ),
        (
            re.compile(
                r"^(?:o\s+projeto\s+)?(?P<subject>.+?)\s+depende\s+de\s+(?P<object>.+)$",
                re.IGNORECASE,
            ),
            "depende_de",
        ),
        (
            re.compile(
                r"^(?P<subject>.+?)\s+pertence\s+(?:a|ao|à)\s+(?P<object>.+)$",
                re.IGNORECASE,
            ),
            "pertence_a",
        ),
        (
            re.compile(
                r"^(?P<subject>.+?)\s+(?:e|é)\s+cliente\s+de\s+(?P<object>.+)$",
                re.IGNORECASE,
            ),
            "cliente_de",
        ),
    )

    _FACT_PATTERNS = (
        (
            re.compile(
                r"^(?P<subject>.+?)\s+(?:tem|possui)\s+(?:o\s+)?status\s+(?P<value>.+)$",
                re.IGNORECASE,
            ),
            "status",
        ),
        (
            re.compile(
                r"^(?P<subject>.+?)\s+usa\s+(?:a\s+)?porta\s+(?P<value>\d{1,5})$",
                re.IGNORECASE,
            ),
            "porta",
        ),
    )

    def __init__(
        self,
        events: EventBus,
        memories: MemoryRepository,
        knowledge: KnowledgeService,
    ) -> None:
        self.events = events
        self.memories = memories
        self.knowledge = knowledge
        events.subscribe("memory.created", self._on_memory_saved)
        events.subscribe("memory.updated", self._on_memory_saved)
        events.subscribe("memory.forgotten", self._on_memory_forgotten)

    def _on_memory_saved(self, event: Event) -> None:
        owner = str(event.payload.get("owner") or "").strip()
        memory_id = int(event.payload.get("memory_id") or 0)
        if not owner or memory_id <= 0:
            return
        try:
            memory = self.memories.get(memory_id, owner)
        except LookupError:
            return
        if not memory.is_active or memory.sensitivity is MemorySensitivity.SECRET:
            return
        created = self.sync_memory(memory)
        self.events.publish(
            "knowledge.memory.synced",
            {
                "owner": owner,
                "memory_id": memory.id,
                "items_created": created,
            },
        )

    def _on_memory_forgotten(self, event: Event) -> None:
        owner = str(event.payload.get("owner") or "").strip()
        memory_id = int(event.payload.get("memory_id") or 0)
        if not owner or memory_id <= 0:
            return
        self.knowledge.repository.deactivate_source(owner=owner, memory_id=memory_id)
        self.events.publish(
            "knowledge.memory.deactivated",
            {"owner": owner, "memory_id": memory_id},
        )

    def sync_memory(self, memory: MemoryRecord) -> int:
        created = 0
        project_entity: KnowledgeEntity | None = None
        if memory.project:
            project_entity = self.knowledge.ensure_entity(
                owner=memory.owner,
                name=memory.project,
                kind=EntityKind.PROJECT,
                sensitivity=memory.sensitivity,
                source_memory_id=memory.id,
            )
            created += 1

        if memory.kind is MemoryKind.PERSON and memory.subject:
            self.knowledge.ensure_entity(
                owner=memory.owner,
                name=memory.subject,
                kind=EntityKind.PERSON,
                sensitivity=memory.sensitivity,
                source_memory_id=memory.id,
            )
            created += 1
        elif memory.kind is MemoryKind.PROJECT and memory.subject:
            subject_entity = project_entity
            if (
                subject_entity is None
                or normalize_knowledge_text(subject_entity.name)
                != normalize_knowledge_text(memory.subject)
            ):
                subject_entity = self.knowledge.ensure_entity(
                    owner=memory.owner,
                    name=memory.subject,
                    kind=EntityKind.PROJECT,
                    sensitivity=memory.sensitivity,
                    source_memory_id=memory.id,
                )
                created += 1
            if memory.metadata.get("origin") == "project.note":
                self.knowledge.add_fact(
                    owner=memory.owner,
                    entity=subject_entity,
                    key="descrição",
                    value=memory.content,
                    sensitivity=memory.sensitivity,
                    confidence=memory.confidence,
                    source_memory_id=memory.id,
                )
                created += 1

        for pattern, predicate in self._RELATION_PATTERNS:
            match = pattern.match(memory.content.strip(" ."))
            if match is None:
                continue
            subject_name = self._clean_entity_name(match.group("subject"))
            object_name = self._clean_entity_name(match.group("object"))
            if not subject_name or not object_name:
                continue
            subject = self.knowledge.ensure_entity(
                owner=memory.owner,
                name=subject_name,
                kind=self._kind_for_name(subject_name, memory, role="subject"),
                sensitivity=memory.sensitivity,
                source_memory_id=memory.id,
            )
            object_ = self.knowledge.ensure_entity(
                owner=memory.owner,
                name=object_name,
                kind=self._kind_for_name(object_name, memory, role="object", predicate=predicate),
                sensitivity=memory.sensitivity,
                source_memory_id=memory.id,
            )
            self.knowledge.add_relation(
                owner=memory.owner,
                subject=subject,
                predicate=predicate,
                object_=object_,
                sensitivity=memory.sensitivity,
                confidence=memory.confidence,
                source_memory_id=memory.id,
            )
            created += 3

        for pattern, key in self._FACT_PATTERNS:
            match = pattern.match(memory.content.strip(" ."))
            if match is None:
                continue
            subject_name = self._clean_entity_name(match.group("subject"))
            value = " ".join(match.group("value").split()).strip(" .")
            if not subject_name or not value:
                continue
            entity = self.knowledge.ensure_entity(
                owner=memory.owner,
                name=subject_name,
                kind=self._kind_for_name(subject_name, memory, role="subject"),
                sensitivity=memory.sensitivity,
                source_memory_id=memory.id,
            )
            self.knowledge.add_fact(
                owner=memory.owner,
                entity=entity,
                key=key,
                value=value,
                sensitivity=memory.sensitivity,
                confidence=memory.confidence,
                source_memory_id=memory.id,
            )
            created += 2
        return created

    @staticmethod
    def _clean_entity_name(value: str) -> str:
        clean = " ".join(str(value or "").split()).strip(" .,-:;")
        clean = re.sub(
            r"^(?:o|a|um|uma|do|da|no|na)\s+(?:projeto|empresa|sistema|servidor|cliente)\s+",
            "",
            clean,
            flags=re.IGNORECASE,
        )
        return clean.strip()

    @staticmethod
    def _kind_for_name(
        name: str,
        memory: MemoryRecord,
        *,
        role: str,
        predicate: str | None = None,
    ) -> EntityKind:
        normalized = normalize_knowledge_text(name)
        project = normalize_knowledge_text(memory.project or "")
        subject = normalize_knowledge_text(memory.subject or "")
        if project and normalized == project:
            return EntityKind.PROJECT
        if subject and normalized == subject:
            if memory.kind is MemoryKind.PERSON:
                return EntityKind.PERSON
            if memory.kind is MemoryKind.PROJECT:
                return EntityKind.PROJECT
        if any(token in normalized.split() for token in ("servidor", "server", "vps")):
            return EntityKind.SYSTEM
        if any(token in normalized.split() for token in ("empresa", "ltda", "sa")):
            return EntityKind.COMPANY
        if predicate == "hospedado_em" and role == "object":
            return EntityKind.SYSTEM
        return EntityKind.CONCEPT
