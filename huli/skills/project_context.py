"""Skill de contexto de projeto da sessão."""

from __future__ import annotations

from huli.brain.context import ContextEngine
from huli.brain.planner import PlannerService
from huli.core.contracts import KernelRequest, KernelResponse
from huli.memory import MemoryEngine, MemoryKind, MemoryPolicyError
from huli.skills.parsing import (
    extract_project_name,
    extract_task_title,
    parse_priority,
    split_project_update,
)


class ProjectContextSkill:
    name = "project-context"
    intents = ("project.set", "project.query", "project.note")

    def __init__(
        self,
        context: ContextEngine,
        planner: PlannerService,
        memory: MemoryEngine,
    ) -> None:
        self.context = context
        self.planner = planner
        self.memory = memory

    def can_handle(self, request: KernelRequest) -> bool:
        return str(request.metadata.get("intent", "")) in self.intents

    def handle(self, request: KernelRequest) -> KernelResponse:
        intent = str(request.metadata.get("intent", ""))
        session_id = str(request.metadata.get("session_id") or "default")
        if intent == "project.note":
            return self._record_note(request, session_id)
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

    def _record_note(
        self,
        request: KernelRequest,
        session_id: str,
    ) -> KernelResponse:
        if str(request.metadata.get("role") or "owner") != "owner":
            return self._response(
                request,
                "As informações de projeto exigem acesso do proprietário.",
                ok=False,
            )
        project = self.context.snapshot(session_id).active_project
        if not project:
            return self._response(
                request,
                "Ative um projeto antes de registrar informações sobre ele.",
                ok=False,
            )

        note, embedded_task = split_project_update(request.text)
        owner = str(request.metadata.get("username") or "owner").strip()
        try:
            memory = self.memory.remember(
                owner=owner,
                content=note,
                kind=MemoryKind.PROJECT,
                subject=project,
                project=project,
                explicit=False,
                confidence=0.98,
                metadata={"origin": "project.note"},
            )
        except (MemoryPolicyError, ValueError) as exc:
            return self._response(
                request,
                f"Não salvei essa informação automaticamente: {exc}",
                ok=False,
            )

        if not embedded_task:
            return self._response(
                request,
                f"Registrei essa informação no projeto {project} como memória #{memory.id}.",
            )

        task_title = extract_task_title(f"precisamos {embedded_task}")
        if not task_title:
            return self._response(
                request,
                f"Registrei essa informação no projeto {project} como memória #{memory.id}.",
            )
        task = self.planner.create_task(
            task_title,
            priority=parse_priority(embedded_task),
            project=project,
        )
        return self._response(
            request,
            (
                f"Registrei essa informação no projeto {project} como memória #{memory.id} "
                f"e criei a tarefa #{task.id}: {task.title}."
            ),
        )

    def _response(self, request: KernelRequest, text: str, *, ok: bool = True) -> KernelResponse:
        return KernelResponse(request_id=request.request_id, text=text, handled_by=self.name, ok=ok)
