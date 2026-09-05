"""Skill de hábitos locais."""

from __future__ import annotations

from datetime import datetime
import re
from zoneinfo import ZoneInfo

from huli.brain.habits import HabitService
from huli.core.contracts import KernelRequest, KernelResponse
from huli.skills.parsing import strip_huli_prefix


class HabitSkill:
    name = "habits"
    intents = ("habit.create", "habit.list", "habit.complete")

    def __init__(self, habits: HabitService, timezone_name: str) -> None:
        self.habits = habits
        self.timezone = ZoneInfo(timezone_name)

    def can_handle(self, request: KernelRequest) -> bool:
        return str(request.metadata.get("intent", "")) in self.intents

    def handle(self, request: KernelRequest) -> KernelResponse:
        intent = str(request.metadata.get("intent", ""))
        owner = str(request.metadata.get("username") or "").strip()
        if not owner:
            return self._response(request, "Essa função exige o proprietário local.", ok=False)
        today = datetime.now(self.timezone).date()
        if intent == "habit.create":
            name = self._extract_name(request.text, complete=False)
            try:
                habit = self.habits.create(owner, name)
            except ValueError as exc:
                return self._response(request, str(exc), ok=False)
            return self._response(request, f"Hábito #{habit.id} criado: {habit.name}.")
        if intent == "habit.complete":
            target = self._extract_name(request.text, complete=True)
            try:
                habit, created = self.habits.mark_done(owner, target, today=today)
            except ValueError as exc:
                return self._response(request, str(exc), ok=False)
            if habit is None:
                return self._response(request, "Não encontrei esse hábito.", ok=False)
            if not created:
                return self._response(request, f"O hábito {habit.name} já estava concluído hoje.")
            return self._response(request, f"Muito bem. Marquei {habit.name} como concluído hoje.")
        statuses = self.habits.status(owner, today=today)
        if not statuses:
            return self._response(request, "Você ainda não cadastrou hábitos.")
        done = sum(item.done_today for item in statuses)
        lines = [f"Hábitos de hoje: {done} de {len(statuses)} concluído(s)."]
        for item in statuses:
            marker = "feito" if item.done_today else "pendente"
            streak = f", sequência {item.current_streak} dia(s)" if item.current_streak else ""
            lines.append(
                f"- #{item.habit.id} {item.habit.name}: {marker} "
                f"({item.completed_last_7_days}/7{streak})"
            )
        return self._response(request, "\n".join(lines))

    @staticmethod
    def _extract_name(text: str, *, complete: bool) -> str:
        value = strip_huli_prefix(text).strip()
        if complete:
            patterns = (
                r"^(?:marque|marcar)\s+(?:o\s+)?h[aá]bito\s+(.+?)\s+como\s+(?:feito|conclu[ií]do)\s*$",
                r"^(?:conclua|concluir|complete|completar)\s+(?:o\s+)?h[aá]bito\s+",
                r"^(?:cumpri|fiz)\s+(?:o\s+)?h[aá]bito\s+",
            )
            for pattern in patterns:
                match = re.match(pattern, value, flags=re.IGNORECASE)
                if match:
                    value = match.group(1) if match.lastindex else value[match.end():]
                    break
        else:
            value = re.sub(
                r"^(?:crie|criar|adicione|adicionar|cadastre|cadastrar)\s+(?:um\s+)?h[aá]bitos?\s+(?:para\s+)?",
                "",
                value,
                flags=re.IGNORECASE,
            )
            value = re.sub(r"^novo\s+h[aá]bito\s*[:\-]?\s*", "", value, flags=re.IGNORECASE)
        return " ".join(value.split()).strip(" #.,:;-")

    def _response(self, request: KernelRequest, text: str, *, ok: bool = True) -> KernelResponse:
        return KernelResponse(request_id=request.request_id, text=text, handled_by=self.name, ok=ok)
