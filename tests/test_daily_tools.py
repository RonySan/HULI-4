"""Testes das ferramentas locais para a rotina diaria."""

from __future__ import annotations

from pathlib import Path

import pytest

from huli.bootstrap import build_runtime
from huli.brain import CalculatorError, TimerService, calculate, format_result, parse_timer_request
from huli.core import KernelRequest
from huli.infrastructure import Settings, SystemHealthSnapshot
from huli.skills import SystemHealthSkill


class _FakeTimer:
    def __init__(self, _seconds, callback, *, args) -> None:
        self.callback = callback
        self.args = args
        self.daemon = False
        self.started = False
        self.cancelled = False

    def start(self) -> None:
        self.started = True

    def cancel(self) -> None:
        self.cancelled = True

    def fire(self) -> None:
        self.callback(*self.args)


def test_calculator_handles_arithmetic_percentage_and_decimal_comma() -> None:
    assert calculate("quanto é 15% de 850?") == pytest.approx(127.5)
    assert calculate("calcule (20 + 5) vezes 2") == pytest.approx(50)
    assert calculate("quanto é 10,5 dividido por 2") == pytest.approx(5.25)
    assert format_result(127.5) == "127,5"


@pytest.mark.parametrize(
    "unsafe",
    (
        "calcule __import__('os').system('dir')",
        "quanto é open('segredo')",
        "calcule 2 elevado a 100",
    ),
)
def test_calculator_rejects_unsafe_or_unbounded_expressions(unsafe: str) -> None:
    with pytest.raises(CalculatorError):
        calculate(unsafe)


def test_computer_health_returns_a_short_local_summary() -> None:
    class Monitor:
        @staticmethod
        def snapshot() -> SystemHealthSnapshot:
            return SystemHealthSnapshot(
                cpu_percent=12,
                memory_percent=54,
                disk_percent=71,
                disk_name="C:",
                battery_percent=80,
                battery_plugged=False,
                uptime_seconds=3 * 3600 + 20 * 60,
            )

    request = KernelRequest.from_text(
        "como está meu computador hoje",
        metadata={"intent": "computer.health"},
    )
    response = SystemHealthSkill(Monitor()).handle(request)  # type: ignore[arg-type]

    assert response.ok is True
    assert response.handled_by == "computer-health"
    assert "processador 12%" in response.text
    assert "memória 54%" in response.text
    assert "ligado há 3h 20min" in response.text


def test_shopping_list_is_persistent_and_separate_from_normal_tasks(tmp_path: Path) -> None:
    runtime = build_runtime(Settings(environment="test", log_level="CRITICAL", data_dir=tmp_path))
    metadata = {"session_id": "daily", "username": "rony", "role": "owner"}

    added = runtime.kernel.process("adicione leite na lista de compras", metadata=metadata)
    runtime.kernel.process("adicionar uma tarefa revisar contrato", metadata=metadata)
    listed = runtime.kernel.process("o que falta comprar", metadata=metadata)
    completed = runtime.kernel.process("já comprei leite", metadata=metadata)

    assert added.handled_by == "shopping"
    assert "leite" in listed.text
    assert "revisar contrato" not in listed.text
    assert completed.ok is True
    assert runtime.planner.pending(project="Compras") == ()
    assert len(runtime.planner.pending()) == 1


def test_timer_notifies_and_leaves_the_active_list() -> None:
    created: list[_FakeTimer] = []

    def factory(*args, **kwargs):
        timer = _FakeTimer(*args, **kwargs)
        created.append(timer)
        return timer

    service = TimerService(clock=lambda: 100.0, timer_factory=factory)  # type: ignore[arg-type]
    alerts = []
    service.subscribe(alerts.append)

    timer = service.create(60, "tirar o bolo do forno")
    assert service.active()[0][1] == 60
    created[0].fire()

    assert service.active() == ()
    assert alerts[0].timer.id == timer.id
    assert alerts[0].message == "Tempo encerrado: tirar o bolo do forno."


def test_timer_parses_spoken_duration_and_can_be_cancelled() -> None:
    duration, label = parse_timer_request("me avise em cinco minutos para desligar a piscina")
    assert duration == 300
    assert label == "desligar a piscina"

    created: list[_FakeTimer] = []

    def factory(*args, **kwargs):
        timer = _FakeTimer(*args, **kwargs)
        created.append(timer)
        return timer

    service = TimerService(clock=lambda: 10.0, timer_factory=factory)  # type: ignore[arg-type]
    timer = service.create(duration, label)
    assert service.cancel(str(timer.id)) == timer
    assert created[0].cancelled is True
