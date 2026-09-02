"""Serviço de tarefas pessoais e de projetos da Huli."""

from __future__ import annotations

from datetime import datetime

from huli.core.events import EventBus
from huli.infrastructure.productivity import TaskRecord, TaskRepository


class PlannerService:
    def __init__(self, repository: TaskRepository, events: EventBus) -> None:
        self.repository = repository
        self.events = events

    def create_task(self, title: str, *, priority: str = "normal", project: str | None = None, due_at: datetime | None = None) -> TaskRecord:
        task = self.repository.create(title, priority=priority, project=project, due_at=due_at)
        self.events.publish("planner.task.created", {"task_id": task.id, "title": task.title, "priority": task.priority, "project": task.project})
        return task

    def pending(self, *, project: str | None = None, limit: int = 20) -> tuple[TaskRecord, ...]:
        return self.repository.list_pending(project=project, limit=limit)

    def complete_task(self, identifier: str, *, project: str | None = None) -> TaskRecord | None:
        task = self.repository.complete(identifier, project=project)
        if task is not None:
            self.events.publish("planner.task.completed", {"task_id": task.id, "title": task.title, "project": task.project})
        return task
