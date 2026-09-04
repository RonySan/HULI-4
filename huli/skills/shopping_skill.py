"""Lista de compras persistente baseada no Planner local."""

from __future__ import annotations

import re

from huli.brain.planner import PlannerService
from huli.core.contracts import KernelRequest, KernelResponse
from huli.skills.parsing import strip_huli_prefix


class ShoppingSkill:
    name = "shopping"
    intents = ("shopping.add", "shopping.list", "shopping.complete")
    _PROJECT = "Compras"

    def __init__(self, planner: PlannerService) -> None:
        self.planner = planner

    def can_handle(self, request: KernelRequest) -> bool:
        return str(request.metadata.get("intent", "")) in self.intents

    def handle(self, request: KernelRequest) -> KernelResponse:
        intent = str(request.metadata.get("intent", ""))
        if intent == "shopping.add":
            item = self._extract_item(request.text, complete=False)
            if not item:
                return self._response(request, "Diga o que deseja adicionar à lista de compras.", ok=False)
            task = self.planner.create_task(item, project=self._PROJECT)
            return self._response(request, f"Adicionei {task.title} à lista de compras.")
        if intent == "shopping.list":
            items = self.planner.pending(project=self._PROJECT, limit=50)
            if not items:
                return self._response(request, "Sua lista de compras está vazia.")
            lines = [f"Faltam {len(items)} item(ns) na lista:"]
            lines.extend(f"- #{item.id} {item.title}" for item in items)
            return self._response(request, "\n".join(lines))
        if intent == "shopping.complete":
            target = self._extract_item(request.text, complete=True)
            if not target:
                return self._response(request, "Diga qual item você já comprou.", ok=False)
            if target.isdigit():
                ids = {str(item.id) for item in self.planner.pending(project=self._PROJECT, limit=200)}
                if target not in ids:
                    return self._response(request, "Esse número não está na lista de compras.", ok=False)
            try:
                task = self.planner.complete_task(target, project=self._PROJECT)
            except ValueError as exc:
                return self._response(request, str(exc), ok=False)
            if task is None:
                return self._response(request, "Não encontrei esse item na lista de compras.", ok=False)
            return self._response(request, f"Certo, marquei {task.title} como comprado.")
        return self._response(request, "Não consegui atualizar a lista de compras.", ok=False)

    @staticmethod
    def _extract_item(text: str, *, complete: bool) -> str:
        value = strip_huli_prefix(text).strip()
        if complete:
            patterns = (
                r"^(?:eu\s+)?(?:j[aá]\s+)?comprei\s+",
                r"^(?:marque|marcar)\s+(.+?)\s+como\s+comprad[oa]\s*$",
                r"^(?:retire|retirar|remova|remover)\s+",
            )
            for pattern in patterns:
                match = re.match(pattern, value, flags=re.IGNORECASE)
                if not match:
                    continue
                value = match.group(1) if match.lastindex else value[match.end():]
                break
        else:
            value = re.sub(
                r"^(?:adicione|adicionar|adiciona|coloque|colocar|inclua|incluir)\s+",
                "",
                value,
                flags=re.IGNORECASE,
            )
            value = re.sub(r"^(?:eu\s+)?preciso\s+comprar\s+", "", value, flags=re.IGNORECASE)
            value = re.sub(r"^(?:lista\s+de\s+compras)\s*[:\-]?\s*", "", value, flags=re.IGNORECASE)
        value = re.sub(
            r"\s+(?:na|a|da|de)\s+(?:minha\s+)?lista\s+de\s+compras\s*$",
            "",
            value,
            flags=re.IGNORECASE,
        )
        return " ".join(value.split()).strip(" #.,:;-")

    def _response(self, request: KernelRequest, text: str, *, ok: bool = True) -> KernelResponse:
        return KernelResponse(request_id=request.request_id, text=text, handled_by=self.name, ok=ok)
