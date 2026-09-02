"""Skill de tarefas do Planner local."""

from __future__ import annotations

from huli.brain.planner import PlannerService
from huli.core.contracts import KernelRequest, KernelResponse
from huli.skills.parsing import extract_completion_target, extract_task_title, parse_priority


class PlannerSkill:
    name = "planner"
    intents = ("task.create", "task.list", "task.complete")

    def __init__(self, planner: PlannerService) -> None:
        self.planner = planner

    def can_handle(self, request: KernelRequest) -> bool:
        return str(request.metadata.get("intent", "")) in self.intents

    def handle(self, request: KernelRequest) -> KernelResponse:
        intent = str(request.metadata.get("intent", ""))
        project = str(request.metadata.get("active_project") or "").strip() or None
        if intent == "task.create":
            title = extract_task_title(request.text)
            if not title:
                return self._response(request, "Não consegui identificar o título da tarefa.", ok=False)
            task = self.planner.create_task(title, priority=parse_priority(request.text), project=project)
            suffix = f" no projeto {task.project}" if task.project else ""
            priority = (
                f" com prioridade {task.priority}"
                if task.priority != "normal"
                else ""
            )
            return self._response(
                request,
                f"Tarefa #{task.id} criada{suffix}{priority}: {task.title}.",
            )
        if intent == "task.list":
            tasks = self.planner.pending(project=project, limit=20)
            if not tasks:
                suffix = f" no projeto {project}" if project else ""
                return self._response(request, f"Não há tarefas pendentes{suffix}.")
            lines = [f"Você tem {len(tasks)} tarefa(s) pendente(s):"]
            for task in tasks:
                priority = f" [{task.priority}]" if task.priority != "normal" else ""
                project_label = f" ({task.project})" if task.project and not project else ""
                lines.append(f"- #{task.id}{priority} {task.title}{project_label}")
            return self._response(request, "\n".join(lines))
        if intent == "task.complete":
            target = extract_completion_target(request.text)
            try:
                task = self.planner.complete_task(target, project=project)
            except ValueError as exc:
                return self._response(request, str(exc), ok=False)
            if task is None:
                return self._response(request, "Não encontrei uma tarefa pendente com esse número ou descrição.", ok=False)
            return self._response(request, f"Tarefa #{task.id} concluída: {task.title}.")
        return self._response(request, "Não consegui executar essa ação do Planner.", ok=False)

    def _response(self, request: KernelRequest, text: str, *, ok: bool = True) -> KernelResponse:
        return KernelResponse(request_id=request.request_id, text=text, handled_by=self.name, ok=ok)
