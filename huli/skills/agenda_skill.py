"""Skill da agenda local da Huli."""

from __future__ import annotations

from datetime import datetime, timedelta
import re

from huli.brain.agenda import AgendaService
from huli.core.contracts import KernelRequest, KernelResponse
from huli.skills.parsing import (
    extract_cancel_target,
    normalize,
    parse_appointment_request,
)


class AgendaSkill:
    name = "agenda"
    intents = ("agenda.create", "agenda.query", "agenda.cancel")

    def __init__(self, agenda: AgendaService, timezone_name: str) -> None:
        self.agenda = agenda
        self.timezone_name = timezone_name

    def can_handle(self, request: KernelRequest) -> bool:
        return str(request.metadata.get("intent", "")) in self.intents

    def handle(self, request: KernelRequest) -> KernelResponse:
        intent = str(request.metadata.get("intent", ""))
        project = str(request.metadata.get("active_project") or "").strip() or None
        if intent == "agenda.create":
            try:
                title, start_at = parse_appointment_request(request.text, timezone_name=self.timezone_name)
            except ValueError as exc:
                return self._response(request, str(exc), ok=False)
            item = self.agenda.create(title, start_at, project=project)
            local = datetime.fromisoformat(item.start_at).astimezone(self.agenda.timezone)
            project_label = f" no projeto {project}" if project else ""
            return self._response(request, f"Compromisso #{item.id} agendado{project_label} para {local.strftime('%d/%m/%Y às %H:%M')}: {item.title}.")
        if intent == "agenda.query":
            normalized = normalize(request.text)
            words = set(re.findall(r"\w+", normalized))
            reference = self.agenda.now()
            period = next((word for word in ("manha", "tarde", "noite") if word in words), None)
            if "amanha" in normalized or "hoje" in normalized or period or normalized in {
                "agenda",
                "agendas",
                "minha agenda",
                "nossa agenda",
            }:
                tomorrow = "amanha" in words
                day = reference.date() + timedelta(days=1 if tomorrow else 0)
                label = "amanhã" if tomorrow else "hoje"
                items = self.agenda.on_date(day)
                if period:
                    start, end, period_label = {"manha": (0, 12, "de manhã"), "tarde": (12, 18, "à tarde"), "noite": (18, 24, "à noite")}[period]
                    items = tuple(item for item in items if start <= datetime.fromisoformat(item.start_at).astimezone(self.agenda.timezone).hour < end)
                    label += f" {period_label}"
                empty_message = f"Não há compromissos para {label}."
                heading = f"Compromissos de {label}:"
            else:
                items = self.agenda.upcoming(reference, limit=10)
                empty_message = "Não há próximos compromissos."
                heading = "Próximos compromissos:"
            if not items:
                return self._response(request, empty_message)
            lines = [heading]
            if "trabalho" in words:
                lines.append("Agenda local; não há separação por calendário de trabalho nesta versão.")
            for item in items:
                local = datetime.fromisoformat(item.start_at).astimezone(self.agenda.timezone)
                lines.append(f"- #{item.id} {local.strftime('%d/%m %H:%M')} — {item.title}")
            return self._response(request, "\n".join(lines))
        if intent == "agenda.cancel":
            target = extract_cancel_target(request.text)
            try:
                item = self.agenda.cancel(target)
            except ValueError as exc:
                return self._response(request, str(exc), ok=False)
            if item is None:
                return self._response(request, "Não encontrei um compromisso ativo com esse número ou descrição.", ok=False)
            return self._response(request, f"Compromisso #{item.id} cancelado: {item.title}.")
        return self._response(request, "Não consegui executar essa ação da Agenda.", ok=False)

    def _response(self, request: KernelRequest, text: str, *, ok: bool = True) -> KernelResponse:
        return KernelResponse(request_id=request.request_id, text=text, handled_by=self.name, ok=ok)
