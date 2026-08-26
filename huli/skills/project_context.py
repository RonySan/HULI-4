"""Skill de contexto de projeto da sessão."""

from __future__ import annotations

from huli.brain.context import ContextEngine
from huli.brain.planner import PlannerService
from huli.core.contracts import KernelRequest, KernelResponse
from huli.skills.parsing import extract_project_name


class ProjectContextSkill:
    name = "project-context"
    intents = ("project.set", "project.query")

    def __init__(self, context: ContextEngine, planner: PlannerService) -> None:
        self.context = context
        self.planner = planner

    def can_handle(self, request: KernelRequest) -> bool:
        return str(request.metadata.get("intent", "")) in self.intents

    def handle(self, request: KernelRequest) -> KernelResponse:
        intent = str(request.metadata.get("intent", ""))
        session_id = str(request.metadata.get("session_id") or "default")
        if intent == "project.set":
            project = extract_project_name(request.text)
            if not project:
                return self._response(request, "Não consegui identificar qual projeto deve ficar ativo.", ok=False)
            self.context.set_active_project(session_id, project)
            return self._response(request, f"Projeto ativo nesta sessão: {project}.")
        explicit = extract_project_name(request.text)
        if explicit:
            self.context.set_active_project(session_id, explicit)
            pending = self.planner.pending(project=explicit, limit=20)
            if pending:
                return self._response(request, f"Projeto {explicit} está ativo nesta sessão e tem {len(pending)} tarefa(s) pendente(s).")
            return self._response(request, f"Projeto {explicit} está ativo nesta sessão. Não há tarefas pendentes vinculadas a ele.")
        snapshot = self.context.snapshot(session_id)
        if snapshot.active_project:
            pending = self.planner.pending(project=snapshot.active_project, limit=20)
            return self._response(request, f"Projeto ativo: {snapshot.active_project}. Tarefas pendentes vinculadas: {len(pending)}.")
        return self._response(request, "Nenhum projeto está ativo nesta sessão. Diga, por exemplo: vamos falar do projeto Medynx.", ok=False)

    def _response(self, request: KernelRequest, text: str, *, ok: bool = True) -> KernelResponse:
        return KernelResponse(request_id=request.request_id, text=text, handled_by=self.name, ok=ok)
