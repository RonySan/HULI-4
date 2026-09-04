"""Regras de acompanhamento diário de hábitos."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from huli.core.events import EventBus
from huli.infrastructure.habits import HabitRecord, HabitRepository


@dataclass(frozen=True, slots=True)
class HabitStatus:
    habit: HabitRecord
    done_today: bool
    current_streak: int
    completed_last_7_days: int


class HabitService:
    def __init__(self, repository: HabitRepository, events: EventBus) -> None:
        self.repository = repository
        self.events = events

    def create(self, owner: str, name: str) -> HabitRecord:
        habit = self.repository.create(owner, name)
        self.events.publish(
            "habits.created", {"habit_id": habit.id, "owner": owner, "name": habit.name}
        )
        return habit

    def mark_done(self, owner: str, identifier: str, *, today: date) -> tuple[HabitRecord | None, bool]:
        habit = self.repository.resolve(owner, identifier)
        if habit is None:
            return None, False
        created = self.repository.mark_done(habit.id, today)
        if created:
            self.events.publish(
                "habits.completed",
                {"habit_id": habit.id, "owner": owner, "completion_date": today.isoformat()},
            )
        return habit, created

    def status(self, owner: str, *, today: date) -> tuple[HabitStatus, ...]:
        since = today - timedelta(days=30)
        results: list[HabitStatus] = []
        for habit in self.repository.list_active(owner):
            dates = self.repository.completion_dates(habit.id, since=since)
            weekly_start = today - timedelta(days=6)
            weekly = sum(1 for item in dates if weekly_start <= item <= today)
            cursor = today if today in dates else today - timedelta(days=1)
            streak = 0
            while cursor in dates:
                streak += 1
                cursor -= timedelta(days=1)
            results.append(
                HabitStatus(
                    habit=habit,
                    done_today=today in dates,
                    current_streak=streak,
                    completed_last_7_days=weekly,
                )
            )
        return tuple(results)
