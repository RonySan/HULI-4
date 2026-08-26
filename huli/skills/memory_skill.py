"""Skill de memória explícita e recuperação de longo prazo."""

from __future__ import annotations

import re

from huli.core.contracts import KernelRequest, KernelResponse
from huli.memory import MemoryEngine, MemoryPolicyError


class MemorySkill:
    name = "memory"
    intents = (
        "memory.remember",
        "memory.recall",
        "memory.list",
        "memory.forget",
    )

    def __init__(self, engine: MemoryEngine) -> None:
        self._engine = engine

    def can_handle(self, request: KernelRequest) -> bool:
        return str(request.metadata.get("intent", "")) in self.intents

    def handle(self, request: KernelRequest) -> KernelResponse:
        intent = str(request.metadata.get("intent", ""))
        owner = str(request.metadata.get("username") or "owner").strip()
        project = str(request.metadata.get("active_project") or "").strip() or None

        try:
            if intent == "memory.remember":
                return self._remember(request, owner, project)
            if intent == "memory.recall":
                return self._recall(request, owner)
            if intent == "memory.list":
                return self._list(request, owner)
            if intent == "memory.forget":
                return self._forget(request, owner)
        except (MemoryPolicyError, ValueError, LookupError) as exc:
            return KernelResponse(
                request_id=request.request_id,
                text=str(exc),
                handled_by=self.name,
                ok=False,
            )

        return KernelResponse(
            request_id=request.request_id,
            text="Não reconheci a operação de memória solicitada.",
            handled_by=self.name,
            ok=False,
        )

    def _remember(
        self,
        request: KernelRequest,
        owner: str,
        project: str | None,
    ) -> KernelResponse:
        content = re.sub(
            r"^\s*(?:huli\s*[,;:]?\s*)?(?:lembre|lembra|guarde|memorize|grave|anote\s+na\s+mem[oó]ria)\s+(?:que\s+)?",
            "",
            request.text,
            flags=re.IGNORECASE,
        ).strip(" .")
        memory = self._engine.remember(
            owner=owner,
            content=content,
            project=project,
            explicit=True,
            confidence=1.0,
        )
        project_note = f" no projeto {memory.project}" if memory.project else ""
        return KernelResponse(
            request_id=request.request_id,
            text=(
                f"Memória #{memory.id} salva como {memory.kind.value}{project_note}."
            ),
            handled_by=self.name,
        )

    def _recall(self, request: KernelRequest, owner: str) -> KernelResponse:
        query = re.sub(
            r"^\s*(?:huli\s*[,;:]?\s*)?(?:o\s+que\s+voc[eê]\s+lembra\s+(?:sobre|de)|voc[eê]\s+lembra\s+(?:sobre|de)|lembra\s+(?:sobre|de))\s+",
            "",
            request.text,
            flags=re.IGNORECASE,
        ).strip(" ?.")
        memories = self._engine.recall(owner=owner, query=query, limit=5)
        if not memories:
            return KernelResponse(
                request_id=request.request_id,
                text=f"Não encontrei nenhuma memória registrada sobre '{query}'.",
                handled_by=self.name,
            )
        lines = [f"Encontrei {len(memories)} memória(s):"]
        lines.extend(
            f"#{memory.id} [{memory.kind.value}] {memory.content}"
            for memory in memories
        )
        return KernelResponse(
            request_id=request.request_id,
            text="\n".join(lines),
            handled_by=self.name,
        )

    def _list(self, request: KernelRequest, owner: str) -> KernelResponse:
        memories = self._engine.list_memories(owner=owner, limit=20)
        if not memories:
            return KernelResponse(
                request_id=request.request_id,
                text="Você ainda não possui memórias de longo prazo registradas.",
                handled_by=self.name,
            )
        lines = [f"Memórias ativas: {len(memories)}"]
        lines.extend(
            f"#{memory.id} [{memory.kind.value}] {memory.content}"
            for memory in memories
        )
        return KernelResponse(
            request_id=request.request_id,
            text="\n".join(lines),
            handled_by=self.name,
        )

    def _forget(self, request: KernelRequest, owner: str) -> KernelResponse:
        target = re.sub(
            r"^\s*(?:huli\s*[,;:]?\s*)?(?:esque[cç]a|esquecer|apague|remova|remove)\s+(?:(?:a|da)\s+mem[oó]ria\s+)?",
            "",
            request.text,
            flags=re.IGNORECASE,
        ).strip(" #?.")
        forgotten = self._engine.forget(owner=owner, target=target)
        return KernelResponse(
            request_id=request.request_id,
            text=f"Memória #{forgotten.id} esquecida.",
            handled_by=self.name,
        )
