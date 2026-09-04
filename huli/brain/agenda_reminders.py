"""Avisos proativos de compromissos proximos."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import threading
from typing import Callable

from huli.brain.agenda import AgendaService
from huli.infrastructure.productivity import AppointmentRecord


@dataclass(frozen=True, slots=True)
class AgendaReminderAlert:
    appointment: AppointmentRecord
    minutes_until: int
    message: str


class AgendaReminderService:
    def __init__(
        self,
        agenda: AgendaService,
        *,
        lead_minutes: int = 15,
        poll_seconds: int = 30,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.agenda = agenda
        self.lead_minutes = max(1, min(int(lead_minutes), 120))
        self.poll_seconds = max(5, min(int(poll_seconds), 300))
        self._clock = clock or agenda.now
        self._lock = threading.RLock()
        self._listeners: list[Callable[[AgendaReminderAlert], None]] = []
        self._announced: set[int] = set()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def subscribe(self, listener: Callable[[AgendaReminderAlert], None]) -> None:
        with self._lock:
            self._listeners.append(listener)

    def check_now(self, now: datetime | None = None) -> tuple[AgendaReminderAlert, ...]:
        reference = (now or self._clock()).astimezone(self.agenda.timezone)
        cutoff = reference + timedelta(minutes=self.lead_minutes)
        alerts: list[AgendaReminderAlert] = []
        for item in self.agenda.upcoming(reference, limit=50):
            start = datetime.fromisoformat(item.start_at).astimezone(self.agenda.timezone)
            if start > cutoff:
                break
            with self._lock:
                if item.id in self._announced:
                    continue
                self._announced.add(item.id)
                listeners = tuple(self._listeners)
            minutes = max(0, int((start - reference).total_seconds() // 60))
            if minutes == 0:
                message = f"Lembrete: {item.title} começa agora, às {start.strftime('%H:%M')}."
            elif minutes == 1:
                message = f"Lembrete: {item.title} começa em 1 minuto, às {start.strftime('%H:%M')}."
            else:
                message = f"Lembrete: {item.title} começa em {minutes} minutos, às {start.strftime('%H:%M')}."
            alert = AgendaReminderAlert(item, minutes, message)
            alerts.append(alert)
            for listener in listeners:
                try:
                    listener(alert)
                except Exception:
                    continue
        return tuple(alerts)

    def start(self) -> None:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop_event = threading.Event()
            self._thread = threading.Thread(
                target=self._run,
                daemon=True,
                name="huli-agenda-reminders",
            )
            self._thread.start()

    def stop(self) -> None:
        with self._lock:
            thread = self._thread
            self._thread = None
            self._stop_event.set()
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=1.0)

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.check_now()
            except Exception:
                pass
            if self._stop_event.wait(self.poll_seconds):
                break
