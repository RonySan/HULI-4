"""Testes de hábitos, foco e avisos proativos da agenda."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from huli.bootstrap import build_runtime
from huli.brain import AgendaReminderService, AgendaService, HabitService
from huli.core import EventBus
from huli.infrastructure import (
    AppointmentRepository,
    HabitRepository,
    Settings,
    SQLiteDatabase,
)


def test_habit_round_trip_and_streak(tmp_path: Path) -> None:
    database = SQLiteDatabase(tmp_path / "huli.db")
    database.initialize()
    habits = HabitService(HabitRepository(database), EventBus())
    today = date(2030, 5, 10)

    habit = habits.create("Rony", "beber água")
    assert habits.mark_done("rony", str(habit.id), today=today) == (habit, True)
    assert habits.mark_done("Rony", "beber agua", today=today) == (habit, False)
    habits.repository.mark_done(habit.id, today - timedelta(days=1))

    status = habits.status("RONY", today=today)[0]
    assert status.done_today is True
    assert status.current_streak == 2
    assert status.completed_last_7_days == 2
    with pytest.raises(ValueError, match="já existe"):
        habits.create("Rony", "Beber Agua")


def test_habit_commands_work_through_the_kernel(tmp_path: Path) -> None:
    runtime = build_runtime(Settings(environment="test", log_level="CRITICAL", data_dir=tmp_path))
    metadata = {"session_id": "habits", "username": "Rony", "role": "owner"}

    created = runtime.kernel.process("criar hábito caminhar", metadata=metadata)
    completed = runtime.kernel.process(
        "marque o hábito caminhar como feito", metadata=metadata
    )
    listed = runtime.kernel.process("meus hábitos", metadata=metadata)

    assert created.handled_by == "habits"
    assert completed.ok is True
    assert "1 de 1" in listed.text
    assert "caminhar: feito" in listed.text


def test_focus_selects_top_task_and_starts_a_session(tmp_path: Path) -> None:
    runtime = build_runtime(Settings(environment="test", log_level="CRITICAL", data_dir=tmp_path))
    metadata = {"session_id": "focus", "username": "Rony", "role": "owner"}
    task = runtime.planner.create_task("enviar proposta", priority="alta")

    priority = runtime.kernel.process("qual é a minha prioridade agora", metadata=metadata)
    started = runtime.kernel.process(
        "iniciar foco por 30 minutos para enviar proposta", metadata=metadata
    )

    assert priority.handled_by == "focus"
    assert f"#{task.id}" in priority.text
    assert "prioridade alta" in priority.text
    assert started.handled_by == "focus"
    assert "30 minutos" in started.text
    assert runtime.timers.active()[0][0].label == "foco em enviar proposta"
    runtime.timers.shutdown()


def test_agenda_reminder_alerts_once_inside_the_lead_window(tmp_path: Path) -> None:
    database = SQLiteDatabase(tmp_path / "huli.db")
    database.initialize()
    timezone = ZoneInfo("America/Sao_Paulo")
    reference = datetime(2030, 5, 10, 8, 0, tzinfo=timezone)
    agenda = AgendaService(AppointmentRepository(database), EventBus(), str(timezone))
    appointment = agenda.create("reunião", reference + timedelta(minutes=10))
    agenda.create("almoço", reference + timedelta(hours=4))
    reminders = AgendaReminderService(
        agenda,
        lead_minutes=15,
        poll_seconds=30,
        clock=lambda: reference,
    )
    received = []
    reminders.subscribe(received.append)

    first = reminders.check_now()
    second = reminders.check_now()

    assert len(first) == 1
    assert first[0].appointment.id == appointment.id
    assert first[0].minutes_until == 10
    assert "começa em 10 minutos" in first[0].message
    assert second == ()
    assert received == [first[0]]


def test_agenda_reminder_warns_once_when_an_appointment_is_late(tmp_path: Path) -> None:
    database = SQLiteDatabase(tmp_path / "huli.db")
    database.initialize()
    timezone = ZoneInfo("America/Sao_Paulo")
    reference = datetime(2030, 5, 10, 8, 10, tzinfo=timezone)
    agenda = AgendaService(AppointmentRepository(database), EventBus(), str(timezone))
    appointment = agenda.create("consulta", reference - timedelta(minutes=5))
    reminders = AgendaReminderService(agenda, lead_minutes=15, late_minutes=10)

    alerts = reminders.check_now(reference)

    assert alerts[0].appointment.id == appointment.id
    assert "começou há 5 minutos" in alerts[0].message


def test_database_schema_includes_habits(tmp_path: Path) -> None:
    database = SQLiteDatabase(tmp_path / "huli.db")
    database.initialize()
    assert database.schema_version() == 10
    with database.connect() as connection:
        tables = {
            str(row["name"])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    assert {"habits", "habit_completions"} <= tables
