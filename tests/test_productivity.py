from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from huli.brain import AgendaService, PlannerService
from huli.core import EventBus
from huli.infrastructure import AppointmentRepository, SQLiteDatabase, TaskRepository


def test_planner_and_agenda_round_trip(tmp_path: Path) -> None:
    db = SQLiteDatabase(tmp_path / "huli.db"); db.initialize(); events = EventBus()
    planner = PlannerService(TaskRepository(db), events)
    agenda = AgendaService(AppointmentRepository(db), events, "America/Sao_Paulo")
    task = planner.create_task("revisar o banco", priority="alta", project="Medynx")
    assert planner.pending(project="Medynx")[0].id == task.id
    assert planner.complete_task(str(task.id)).status == "completed"
    tz = ZoneInfo("America/Sao_Paulo")
    item = agenda.create("dentista", datetime(2030, 5, 10, 15, 0, tzinfo=tz))
    assert agenda.today(datetime(2030, 5, 10, 9, 0, tzinfo=tz))[0].id == item.id
    assert agenda.cancel(str(item.id)).status == "cancelled"
