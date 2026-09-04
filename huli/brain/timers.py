"""Temporizadores locais de curta duracao."""

from __future__ import annotations

from dataclasses import dataclass
import re
import threading
import time
from typing import Callable

from huli.brain.normalization import normalize_text


@dataclass(frozen=True, slots=True)
class TimerRecord:
    id: int
    label: str
    duration_seconds: int
    deadline: float


@dataclass(frozen=True, slots=True)
class TimerAlert:
    timer: TimerRecord
    message: str


class TimerService:
    def __init__(
        self,
        *,
        clock: Callable[[], float] = time.monotonic,
        timer_factory: Callable[..., threading.Timer] = threading.Timer,
    ) -> None:
        self._clock = clock
        self._timer_factory = timer_factory
        self._lock = threading.RLock()
        self._next_id = 1
        self._active: dict[int, tuple[TimerRecord, threading.Timer]] = {}
        self._listeners: list[Callable[[TimerAlert], None]] = []

    def subscribe(self, listener: Callable[[TimerAlert], None]) -> None:
        with self._lock:
            self._listeners.append(listener)

    def create(self, duration_seconds: int, label: str) -> TimerRecord:
        duration = int(duration_seconds)
        if duration < 1 or duration > 24 * 60 * 60:
            raise ValueError("O temporizador precisa durar entre 1 segundo e 24 horas.")
        clean_label = " ".join(str(label or "").split()).strip(" .,-")
        with self._lock:
            identifier = self._next_id
            self._next_id += 1
            record = TimerRecord(
                id=identifier,
                label=clean_label,
                duration_seconds=duration,
                deadline=self._clock() + duration,
            )
            worker = self._timer_factory(duration, self._finish, args=(identifier,))
            worker.daemon = True
            self._active[identifier] = (record, worker)
            worker.start()
        return record

    def active(self) -> tuple[tuple[TimerRecord, int], ...]:
        now = self._clock()
        with self._lock:
            records = sorted(self._active.values(), key=lambda item: item[0].deadline)
            return tuple(
                (record, max(0, int(round(record.deadline - now))))
                for record, _worker in records
            )

    def cancel(self, identifier: str) -> TimerRecord | None:
        value = " ".join(str(identifier or "").split()).strip(" #.,")
        if not value.isdigit():
            return None
        with self._lock:
            managed = self._active.pop(int(value), None)
        if managed is None:
            return None
        record, worker = managed
        worker.cancel()
        return record

    def shutdown(self) -> None:
        with self._lock:
            active = tuple(self._active.values())
            self._active.clear()
        for _record, worker in active:
            worker.cancel()

    def _finish(self, identifier: int) -> None:
        with self._lock:
            managed = self._active.pop(identifier, None)
            listeners = tuple(self._listeners)
        if managed is None:
            return
        record = managed[0]
        subject = record.label or format_duration(record.duration_seconds)
        alert = TimerAlert(timer=record, message=f"Tempo encerrado: {subject}.")
        for listener in listeners:
            try:
                listener(alert)
            except Exception:
                continue


_NUMBERS = {
    "um": 1,
    "uma": 1,
    "dois": 2,
    "duas": 2,
    "tres": 3,
    "quatro": 4,
    "cinco": 5,
    "seis": 6,
    "sete": 7,
    "oito": 8,
    "nove": 9,
    "dez": 10,
    "quinze": 15,
    "vinte": 20,
    "trinta": 30,
    "quarenta": 40,
    "cinquenta": 50,
    "sessenta": 60,
}


def parse_timer_request(text: str) -> tuple[int, str]:
    normalized = normalize_text(text)
    normalized = re.sub(r"^huli\s+", "", normalized).strip()
    number_pattern = "|".join(sorted(_NUMBERS, key=len, reverse=True))
    match = re.search(
        rf"\b(?P<number>\d{{1,5}}|{number_pattern})\s*(?P<unit>segundos?|minutos?|horas?)\b",
        normalized,
    )
    if match is None:
        raise ValueError("Informe a duração, por exemplo: temporizador de 10 minutos.")
    token = match.group("number")
    amount = int(token) if token.isdigit() else _NUMBERS[token]
    unit = match.group("unit")
    multiplier = 1 if unit.startswith("segundo") else 60 if unit.startswith("minuto") else 3600
    duration = amount * multiplier
    trailing = normalized[match.end():].strip()
    label = re.sub(r"^(?:para|do|da)\s+", "", trailing).strip()
    if not label:
        label = f"temporizador de {format_duration(duration)}"
    return duration, label


def extract_timer_identifier(text: str) -> str:
    normalized = normalize_text(text)
    match = re.search(r"(?:timer|temporizador|cronometro)\s*(?:numero\s*)?#?(\d+)", normalized)
    return match.group(1) if match else ""


def format_duration(seconds: int) -> str:
    if seconds % 3600 == 0:
        value = seconds // 3600
        return f"{value} hora" + ("s" if value != 1 else "")
    if seconds % 60 == 0:
        value = seconds // 60
        return f"{value} minuto" + ("s" if value != 1 else "")
    return f"{seconds} segundo" + ("s" if seconds != 1 else "")
