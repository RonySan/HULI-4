"""Orientacao objetiva de prioridade e sessoes de foco."""

from __future__ import annotations

from datetime import datetime
import re

from huli.brain.agenda import AgendaService
from huli.brain.normalization import normalize_text
from huli.brain.planner import PlannerService
from huli.brain.timers import TimerService, format_duration
from huli.core.contracts import KernelRequest, KernelResponse


class FocusSkill:
    name = "focus"
    intents = ("focus.start", "focus.next")

    _NUMBERS = {
        "um": 1,
        "uma": 1,
        "cinco": 5,
        "dez": 10,
        "quinze": 15,
        "vinte": 20,
        "vinte e cinco": 25,
        "trinta": 30,
        "quarenta": 40,
        "quarenta e cinco": 45,
        "cinquenta": 50,
        "sessenta": 60,
    }

    def __init__(
        self,
        timers: TimerService,
        planner: PlannerService,
        agenda: AgendaService,
    ) -> None:
        self.timers = timers
        self.planner = planner
        self.agenda = agenda

    def can_handle(self, request: KernelRequest) -> bool:
        return str(request.metadata.get("intent", "")) in self.intents

    def handle(self, request: KernelRequest) -> KernelResponse:
        intent = str(request.metadata.get("intent", ""))
        if intent == "focus.start":
            duration, subject = self._parse_focus(request.text)
            label = f"foco em {subject}" if subject else "sessão de foco"
            timer = self.timers.create(duration, label)
            detail = f" em {subject}" if subject else ""
            return self._response(
                request,
                f"Foco iniciado por {format_duration(duration)}{detail}. "
                f"Eu aviso quando terminar; temporizador #{timer.id}.",
            )
        return self._response(request, self._next_priority())

    def _next_priority(self) -> str:
        now = self.agenda.now()
        upcoming = self.agenda.upcoming(now, limit=1)
        appointment = upcoming[0] if upcoming else None
        if appointment is not None:
            start = datetime.fromisoformat(appointment.start_at).astimezone(self.agenda.timezone)
            minutes = max(0, int((start - now).total_seconds() // 60))
            if minutes <= 90:
                return (
                    f"Sua prioridade agora é se preparar para {appointment.title}, "
                    f"às {start.strftime('%H:%M')} — faltam cerca de {minutes} minutos."
                )
        tasks = tuple(
            task
            for task in self.planner.pending(limit=20)
            if (task.project or "").casefold() != "compras"
        )
        if tasks:
            task = tasks[0]
            priority = " de prioridade alta" if task.priority == "alta" else ""
            return f"Sua prioridade agora é a tarefa #{task.id}{priority}: {task.title}."
        if appointment is not None:
            start = datetime.fromisoformat(appointment.start_at).astimezone(self.agenda.timezone)
            return f"Sem tarefa urgente. Seu próximo compromisso é {appointment.title}, às {start.strftime('%H:%M')}."
        return "Sua agenda está livre e não há tarefas pendentes."

    @classmethod
    def _parse_focus(cls, text: str) -> tuple[int, str]:
        normalized = normalize_text(text)
        words = "|".join(re.escape(item) for item in sorted(cls._NUMBERS, key=len, reverse=True))
        match = re.search(rf"\b(?P<number>\d{{1,3}}|{words})\s*(?P<unit>minutos?|horas?)\b", normalized)
        duration = 25 * 60
        tail_start = 0
        if match:
            token = match.group("number")
            amount = int(token) if token.isdigit() else cls._NUMBERS[token]
            multiplier = 3600 if match.group("unit").startswith("hora") else 60
            duration = amount * multiplier
            tail_start = match.end()
        if duration < 60 or duration > 4 * 3600:
            raise ValueError("A sessão de foco precisa durar entre 1 minuto e 4 horas.")
        trailing = normalized[tail_start:].strip() if match else normalized
        subject_match = re.search(r"\b(?:para|em)\s+(.+)$", trailing)
        subject = subject_match.group(1).strip() if subject_match else ""
        return duration, subject

    def _response(self, request: KernelRequest, text: str, *, ok: bool = True) -> KernelResponse:
        return KernelResponse(request_id=request.request_id, text=text, handled_by=self.name, ok=ok)
