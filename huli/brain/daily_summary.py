"""Resumo objetivo do dia baseado em dados reais da Huli."""

from __future__ import annotations

from datetime import datetime

from huli.brain.agenda import AgendaService
from huli.brain.planner import PlannerService


class DailySummaryService:
    def __init__(self, planner: PlannerService, agenda: AgendaService) -> None:
        self.planner = planner
        self.agenda = agenda

    def build(self, now: datetime | None = None, *, project: str | None = None) -> str:
        tasks = self.planner.pending(project=project, limit=10)
        appointments = self.agenda.today(now)
        lines: list[str] = []
        if appointments:
            lines.append(f"Hoje você tem {len(appointments)} compromisso(s):")
            for item in appointments:
                start = datetime.fromisoformat(item.start_at).astimezone(self.agenda.timezone)
                lines.append(f"- #{item.id} {start.strftime('%H:%M')} — {item.title}")
        else:
            lines.append("Hoje não há compromissos agendados.")
        if tasks:
            scope = f" do projeto {project}" if project else ""
            lines.append(f"Você tem {len(tasks)} tarefa(s) pendente(s){scope}:")
            for task in tasks:
                label = f" [{task.priority}]" if task.priority != "normal" else ""
                lines.append(f"- #{task.id}{label} {task.title}")
        else:
            lines.append("Não há tarefas pendentes nesse contexto." if project else "Não há tarefas pendentes.")
        return "\n".join(lines)
