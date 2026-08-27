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

    def cancel(self, identifier: str) -> AppointmentRecord | None:
        appointment = self.repository.cancel(identifier)
        if appointment is not None:
            self.events.publish("agenda.appointment.cancelled", {"appointment_id": appointment.id, "title": appointment.title, "start_at": appointment.start_at})
        return appointment
