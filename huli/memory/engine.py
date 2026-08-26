"""Memory Engine 4.0: armazenamento e recuperação determinísticos."""

from __future__ import annotations

from datetime import datetime
import re
import unicodedata

from huli.core.events import EventBus
from huli.memory.models import (
    MemoryCandidate,
    MemoryKind,
    MemoryRecord,
    MemorySensitivity,
    MemorySource,
)
from huli.memory.policy import MemoryPolicy
from huli.memory.repository import MemoryRepository


def normalize_memory_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", str(value or "").casefold())
    without_accents = "".join(
        char for char in decomposed if not unicodedata.combining(char)
    )
    cleaned = re.sub(r"[^a-z0-9]+", " ", without_accents)
    return " ".join(cleaned.split()).strip()


def _tokens(value: str) -> set[str]:
    return {token for token in normalize_memory_text(value).split() if len(token) >= 2}


class MemoryEngine:
    """Coordena políticas, persistência, busca e esquecimento de memória."""

    def __init__(
        self,
        repository: MemoryRepository,
        policy: MemoryPolicy,
        event_bus: EventBus,
    ) -> None:
        self.repository = repository
        self.policy = policy
        self.events = event_bus

    def infer_kind(self, content: str, *, project: str | None = None) -> MemoryKind:
        text = normalize_memory_text(content)
        if project or " projeto " in f" {text} ":
            return MemoryKind.PROJECT
        if any(term in text for term in ("prefiro", "gosto de", "nao gosto", "preferencia")):
            return MemoryKind.PREFERENCE
        if any(
            term in text
            for term in (
                "minha esposa",
                "meu marido",
                "meu filho",
                "minha filha",
                "meu cliente",
                "minha cliente",
            )
        ):
            return MemoryKind.PERSON
        if re.search(r"\b(?:hoje|ontem|amanha|\d{1,2}/\d{1,2}|20\d{2})\b", text):
            return MemoryKind.TEMPORAL
        if any(term in text for term in ("aconteceu", "fizemos", "eu fiz", "ocorreu")):
            return MemoryKind.EPISODIC
        return MemoryKind.SEMANTIC

    def remember(
        self,
        *,
        owner: str,
        content: str,
        kind: MemoryKind | None = None,
        subject: str | None = None,
        project: str | None = None,
        explicit: bool = True,
        source: MemorySource | None = None,
        confidence: float = 1.0,
        sensitivity: MemorySensitivity | None = None,
        occurred_at: datetime | None = None,
        valid_until: datetime | None = None,
        metadata: dict[str, object] | None = None,
    ) -> MemoryRecord:
        normalized_owner = " ".join(str(owner or "").split()).strip()
        if not normalized_owner:
            raise ValueError("A memória precisa estar vinculada a um proprietário.")

        clean_content = self.policy.validate_content(content)
        resolved_kind = kind or self.infer_kind(clean_content, project=project)
        resolved_sensitivity = sensitivity or self.policy.classify_sensitivity(clean_content)
        resolved_source = source or (
            MemorySource.EXPLICIT if explicit else MemorySource.AUTOMATIC
        )
        self.policy.validate_store(
            content=clean_content,
            kind=resolved_kind,
            sensitivity=resolved_sensitivity,
            explicit=explicit,
            confidence=confidence,
        )

        record, created = self.repository.upsert(
            owner=normalized_owner,
            kind=resolved_kind,
            content=clean_content,
            normalized_content=normalize_memory_text(clean_content),
            subject=" ".join(str(subject or "").split()).strip() or None,
            project=" ".join(str(project or "").split()).strip() or None,
            sensitivity=resolved_sensitivity,
            source=resolved_source,
            confidence=max(0.0, min(float(confidence), 1.0)),
            occurred_at=occurred_at,
            valid_until=valid_until,
            metadata=metadata,
        )
        self.events.publish(
            "memory.created" if created else "memory.updated",
            {
                "memory_id": record.id,
                "owner": record.owner,
                "kind": record.kind.value,
                "source": record.source.value,
                "sensitivity": record.sensitivity.value,
            },
        )
        return record

    def remember_candidate(self, candidate: MemoryCandidate) -> MemoryRecord:
        return self.remember(
            owner=candidate.owner,
            content=candidate.content,
            kind=candidate.kind,
            subject=candidate.subject,
            project=candidate.project,
            explicit=False,
            source=MemorySource.AUTOMATIC,
            confidence=candidate.confidence,
            metadata=candidate.metadata,
        )

    def recall(
        self,
        *,
        owner: str,
        query: str,
        project: str | None = None,
        limit: int = 5,
    ) -> tuple[MemoryRecord, ...]:
        normalized_query = normalize_memory_text(query)
        if not normalized_query:
            return ()
        query_tokens = _tokens(normalized_query)
        candidates = self.repository.list_active(owner, project=project, limit=200)
        scored: list[tuple[float, MemoryRecord]] = []

        for memory in candidates:
            score = self._score(memory, normalized_query, query_tokens)
            if score > 0:
                scored.append((score, memory))

        scored.sort(key=lambda item: (item[0], item[1].updated_at), reverse=True)
        matches = tuple(memory for _score, memory in scored[: max(1, min(limit, 20))])
        for memory in matches:
            self.repository.record_access(memory.id, owner)

        self.events.publish(
            "memory.recalled",
            {
                "owner": owner,
                "query": normalized_query,
                "memory_ids": [memory.id for memory in matches],
                "count": len(matches),
            },
        )
        return matches

    def list_memories(
        self,
        *,
        owner: str,
        kind: MemoryKind | None = None,
        project: str | None = None,
        limit: int = 20,
    ) -> tuple[MemoryRecord, ...]:
        return self.repository.list_active(
            owner,
            kind=kind,
            project=project,
            limit=limit,
        )

    def forget(self, *, owner: str, target: str) -> MemoryRecord:
        clean_target = " ".join(str(target or "").split()).strip(" #.,")
        if not clean_target:
            raise LookupError("Informe qual memória deve ser esquecida.")

        if clean_target.isdigit():
            memory = self.repository.get(int(clean_target), owner)
            if not memory.is_active:
                raise LookupError("Essa memória já está inativa.")
        else:
            exact = normalize_memory_text(clean_target)
            active = self.repository.list_active(owner, limit=200)
            exact_matches = [
                memory
                for memory in active
                if memory.normalized_content == exact
                or normalize_memory_text(memory.subject or "") == exact
            ]
            if len(exact_matches) == 1:
                memory = exact_matches[0]
            elif len(exact_matches) > 1:
                raise LookupError(
                    "Há mais de uma memória com esse conteúdo. Use o número da memória."
                )
            else:
                recalled = self.recall(owner=owner, query=clean_target, limit=2)
                if len(recalled) != 1:
                    raise LookupError(
                        "Não encontrei uma única memória segura para esquecer. Use o número dela."
                    )
                memory = recalled[0]

        forgotten = self.repository.forget(memory.id, owner)
        self.events.publish(
            "memory.forgotten",
            {
                "memory_id": forgotten.id,
                "owner": owner,
                "kind": forgotten.kind.value,
            },
        )
        return forgotten

    @staticmethod
    def _score(
        memory: MemoryRecord,
        normalized_query: str,
        query_tokens: set[str],
    ) -> float:
        content = memory.normalized_content
        if content == normalized_query:
            return 10.0
        score = 0.0
        if normalized_query in content or content in normalized_query:
            score += 5.0
        memory_tokens = _tokens(content)
        if query_tokens and memory_tokens:
            overlap = len(query_tokens & memory_tokens)
            score += 4.0 * overlap / len(query_tokens)
        subject = normalize_memory_text(memory.subject or "")
        project = normalize_memory_text(memory.project or "")
        if subject and (normalized_query in subject or subject in normalized_query):
            score += 2.5
        if project and (normalized_query in project or project in normalized_query):
            score += 2.5
        return score
