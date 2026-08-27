"""Skill da agenda local da Huli."""

from __future__ import annotations

from datetime import datetime, timedelta

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
            reference = self.agenda.now()
            if "amanha" in normalized:
                items = self.agenda.on_date(reference.date() + timedelta(days=1))
                empty_message = "Não há compromissos para amanhã."
                heading = "Compromissos de amanhã:"
            elif "noite" in normalized:
                items = tuple(
                    item
                    for item in self.agenda.today(reference)
                    if datetime.fromisoformat(item.start_at).astimezone(
                        self.agenda.timezone
                    ).hour
                    >= 18
                )
                empty_message = "Não há compromissos para esta noite."
                heading = "Compromissos desta noite:"
            elif "hoje" in normalized or normalized in {
                "agenda",
                "minha agenda",
                "nossa agenda",
            }:
                items = self.agenda.today(reference)
                empty_message = "Não há compromissos para hoje."
                heading = "Compromissos de hoje:"
            else:
                items = self.agenda.upcoming(reference, limit=10)
                empty_message = "Não há próximos compromissos."
                heading = "Próximos compromissos:"
            if not items:
                return self._response(request, empty_message)
            lines = [heading]
            for item in items:
                local = datetime.fromisoformat(item.start_at).astimezone(self.agenda.timezone)
                lines.append(f"- #{item.id} {local.strftime('%d/%m %H:%M')} — {item.title}")
            return self._response(request, "\n".join(lines))
        if intent == "agenda.cancel":
            target = extract_cancel_target(request.text)
            item = self.agenda.cancel(target)
            if item is None:
                return self._response(request, "Não encontrei um compromisso ativo com esse número ou descrição.", ok=False)
            return self._response(request, f"Compromisso #{item.id} cancelado: {item.title}.")
        return self._response(request, "Não consegui executar essa ação da Agenda.", ok=False)

    def _response(self, request: KernelRequest, text: str, *, ok: bool = True) -> KernelResponse:
        return KernelResponse(request_id=request.request_id, text=text, handled_by=self.name, ok=ok)
