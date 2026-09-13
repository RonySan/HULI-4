"""Agenda local da Huli."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from huli.core.events import EventBus
from huli.infrastructure.productivity import AppointmentRecord, AppointmentRepository


class AgendaService:
    def __init__(self, repository: AppointmentRepository, events: EventBus, timezone_name: str) -> None:
        self.repository = repository
        self.events = events
        self.timezone = ZoneInfo(timezone_name)

    def now(self) -> datetime:
        return datetime.now(self.timezone)

    def create(self, title: str, start_at: datetime, *, project: str | None = None) -> AppointmentRecord:
        appointment = self.repository.create(title, start_at, project=project)
        self.events.publish("agenda.appointment.created", {"appointment_id": appointment.id, "title": appointment.title, "start_at": appointment.start_at, "project": appointment.project})
        return appointment

    def today(self, now: datetime | None = None) -> tuple[AppointmentRecord, ...]:
        reference = (now or self.now()).astimezone(self.timezone)
        return self.on_date(reference.date())

    def on_date(self, target: date) -> tuple[AppointmentRecord, ...]:
        start = datetime(
            target.year,
            target.month,
            target.day,
            tzinfo=self.timezone,
        )
        end = start + timedelta(days=1)
        return self.repository.list_between(start, end)

    def upcoming(self, now: datetime | None = None, limit: int = 20) -> tuple[AppointmentRecord, ...]:
        reference = (now or self.now()).astimezone(self.timezone)
        return self.repository.list_upcoming(reference, limit=limit)

    def between(self, start_at: datetime, end_at: datetime, *, limit: int = 50) -> tuple[AppointmentRecord, ...]:
        start = start_at.astimezone(self.timezone)
        end = end_at.astimezone(self.timezone)
        return self.repository.list_between(start, end, limit=limit)

    def suggestions(
        self,
        items: tuple[AppointmentRecord, ...] | None = None,
        *,
        now: datetime | None = None,
    ) -> tuple[str, ...]:
        """Gera poucas sugestões úteis a partir do contexto real da agenda."""
        reference = (now or self.now()).astimezone(self.timezone)
        appointments = tuple(items) if items is not None else self.today(reference)
        ordered = sorted(
            appointments,
            key=lambda item: datetime.fromisoformat(item.start_at),
        )
        suggestions: list[str] = []
        for current, following in zip(ordered, ordered[1:]):
            current_start = datetime.fromisoformat(current.start_at).astimezone(self.timezone)
            current_end = (
                datetime.fromisoformat(current.end_at).astimezone(self.timezone)
                if current.end_at
                else current_start + timedelta(hours=1)
            )
            following_start = datetime.fromisoformat(following.start_at).astimezone(
                self.timezone
            )
            gap = int((following_start - current_end).total_seconds() // 60)
            if gap < 0:
                suggestions.append(
                    f"Atenção: “{current.title}” e “{following.title}” têm conflito de horário."
                )
                break
            if gap < 20:
                suggestions.append(
                    f"Reserve um intervalo: há apenas {gap} minutos entre “{current.title}” e “{following.title}”."
                )
                break
        upcoming = [
            item
            for item in ordered
            if datetime.fromisoformat(item.start_at).astimezone(self.timezone) >= reference
        ]
        if upcoming:
            next_item = upcoming[0]
            next_start = datetime.fromisoformat(next_item.start_at).astimezone(self.timezone)
            minutes = int((next_start - reference).total_seconds() // 60)
            if 0 <= minutes <= 60:
                suggestions.append(
                    f"Prepare-se para “{next_item.title}”, que começa em {minutes} minutos."
                )
        if len(ordered) >= 5 and len(suggestions) < 2:
            suggestions.append("Seu dia está cheio; vale reservar pequenas pausas entre os compromissos.")
        return tuple(suggestions[:2])

    def suggestion_for_slot(
        self,
        start_at: datetime,
        *,
        duration_minutes: int = 60,
    ) -> str | None:
        """Avalia conflito ou intervalo curto antes de criar um compromisso."""
        local_start = start_at.astimezone(self.timezone)
        local_end = local_start + timedelta(minutes=max(1, duration_minutes))
        for item in self.on_date(local_start.date()):
            existing_start = datetime.fromisoformat(item.start_at).astimezone(self.timezone)
            existing_end = (
                datetime.fromisoformat(item.end_at).astimezone(self.timezone)
                if item.end_at
                else existing_start + timedelta(hours=1)
            )
            if local_start < existing_end and local_end > existing_start:
                return f"Atenção: esse horário coincide com “{item.title}”."
            gap_before = int((local_start - existing_end).total_seconds() // 60)
            gap_after = int((existing_start - local_end).total_seconds() // 60)
            gap = next((value for value in (gap_before, gap_after) if 0 <= value < 20), None)
            if gap is not None:
                return f"Sugestão: deixe mais intervalo; serão apenas {gap} minutos perto de “{item.title}”."
        return None

    def cancel(self, identifier: str) -> AppointmentRecord | None:
        appointment = self.repository.cancel(identifier)
        if appointment is not None:
            self.events.publish("agenda.appointment.cancelled", {"appointment_id": appointment.id, "title": appointment.title, "start_at": appointment.start_at})
        return appointment

    def complete(self, identifier: str) -> AppointmentRecord | None:
        appointment = self.repository.complete(identifier)
        if appointment is not None:
            self.events.publish(
                "agenda.appointment.completed",
                {
                    "appointment_id": appointment.id,
                    "title": appointment.title,
                    "start_at": appointment.start_at,
                },
            )
        return appointment
