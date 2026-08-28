"""Skill de consulta ao Personal Knowledge Graph."""

from __future__ import annotations

import re

from huli.core.contracts import KernelRequest, KernelResponse
from huli.knowledge import KnowledgeService


_PREDICATE_LABELS = {
    "desenvolvido_por": "desenvolvido por",
    "hospedado_em": "hospedado em",
    "depende_de": "depende de",
    "pertence_a": "pertence a",
    "cliente_de": "cliente de",
}


class KnowledgeSkill:
    name = "knowledge"
    intents = ("knowledge.describe", "knowledge.relation")

    def __init__(self, knowledge: KnowledgeService) -> None:
        self._knowledge = knowledge

    def can_handle(self, request: KernelRequest) -> bool:
        return str(request.metadata.get("intent", "")) in self.intents

    def handle(self, request: KernelRequest) -> KernelResponse:
        if str(request.metadata.get("role") or "owner") != "owner":
            return KernelResponse(
                request_id=request.request_id,
                text="O conhecimento pessoal exige acesso do proprietário.",
                handled_by=self.name,
                ok=False,
            )
        owner = str(request.metadata.get("username") or "owner").strip()
        intent = str(request.metadata.get("intent") or "")
        try:
            if intent == "knowledge.describe":
                return self._describe(request, owner)
            if intent == "knowledge.relation":
                return self._relation(request, owner)
        except LookupError as exc:
            return KernelResponse(
                request_id=request.request_id,
                text=str(exc),
                handled_by=self.name,
                ok=False,
            )
        return KernelResponse(
            request_id=request.request_id,
            text="Não reconheci a consulta de conhecimento.",
            handled_by=self.name,
            ok=False,
        )

    def _describe(self, request: KernelRequest, owner: str) -> KernelResponse:
        query = re.sub(
            r"^\s*(?:huli\s*[,;:]?\s*)?(?:o\s+que\s+voc[eê]\s+sabe\s+(?:sobre|de)|fale\s+(?:sobre|do|da)|informa[cç][oõ]es\s+(?:sobre|de))\s+",
            "",
            request.text,
            flags=re.IGNORECASE,
        ).strip(" ?.")
        snapshot = self._knowledge.describe(owner=owner, query=query)
        lines = [f"{snapshot.entity.name} [{snapshot.entity.kind.value}]"]
        for fact in snapshot.facts:
            lines.append(f"- {fact.key}: {fact.value}")
        seen_relations: set[tuple[str, int, str]] = set()
        for relation, target in snapshot.outgoing:
            key = (relation.predicate, target.id, "out")
            if key in seen_relations:
                continue
            seen_relations.add(key)
            label = _PREDICATE_LABELS.get(relation.predicate, relation.predicate.replace("_", " "))
            lines.append(f"- {label}: {target.name}")
        for relation, source in snapshot.incoming:
            key = (relation.predicate, source.id, "in")
            if key in seen_relations:
                continue
            seen_relations.add(key)
            label = _PREDICATE_LABELS.get(relation.predicate, relation.predicate.replace("_", " "))
            lines.append(f"- relação inversa ({label}): {source.name}")
        if len(lines) == 1:
            lines.append("- entidade registrada, sem fatos ou relações ativas.")
        return KernelResponse(
            request_id=request.request_id,
            text="\n".join(lines),
            handled_by=self.name,
        )

    def _relation(self, request: KernelRequest, owner: str) -> KernelResponse:
        subject, predicate = self._parse_relation_question(request.text)
        targets = self._knowledge.related(
            owner=owner,
            subject_query=subject,
            predicate=predicate,
        )
        if not targets:
            label = _PREDICATE_LABELS.get(predicate, predicate.replace("_", " "))
            return KernelResponse(
                request_id=request.request_id,
                text=f"Não há relação registrada '{label}' para {subject}.",
                handled_by=self.name,
                ok=False,
            )
        names = ", ".join(target.name for target in targets)
        if predicate == "desenvolvido_por":
            text = f"{subject} é desenvolvido por {names}."
        elif predicate == "hospedado_em":
            text = f"{subject} está hospedado em {names}."
        elif predicate == "depende_de":
            text = f"{subject} depende de {names}."
        elif predicate == "pertence_a":
            text = f"{subject} pertence a {names}."
        elif predicate == "cliente_de":
            text = f"{subject} é cliente de {names}."
        else:
            text = f"{subject}: {predicate} → {names}."
        return KernelResponse(
            request_id=request.request_id,
            text=text,
            handled_by=self.name,
        )

    @staticmethod
    def _parse_relation_question(text: str) -> tuple[str, str]:
        raw = re.sub(r"^\s*huli\s*[,;:]?\s*", "", text, flags=re.IGNORECASE).strip(" ?.")
        rules = (
            (r"^quem\s+(?:desenvolve|desenvolveu)\s+(?:o\s+|a\s+)?(.+)$", "desenvolvido_por"),
            (r"^onde\s+(?:o\s+|a\s+)?(.+?)\s+(?:esta|está|fica)\s+hospedad[oa]$", "hospedado_em"),
            (r"^qual\s+servidor\s+hospeda\s+(?:o\s+|a\s+)?(.+)$", "hospedado_em"),
            (r"^do\s+que\s+(?:o\s+|a\s+)?(.+?)\s+depende$", "depende_de"),
            (r"^(?:a\s+que|a\s+quem)\s+(?:o\s+|a\s+)?(.+?)\s+pertence$", "pertence_a"),
            (r"^de\s+quem\s+(?:o\s+|a\s+)?(.+?)\s+(?:e|é)\s+cliente$", "cliente_de"),
        )
        for pattern, predicate in rules:
            match = re.match(pattern, raw, flags=re.IGNORECASE)
            if match:
                subject = " ".join(match.group(1).split()).strip(" ?.")
                return subject, predicate
        raise LookupError("Não consegui determinar qual relação de conhecimento foi solicitada.")
