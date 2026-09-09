"""Regressões do registro local de inicialização automática."""

from pathlib import Path

from huli.desktop.startup_report import StartupReporter


def test_startup_report_tracks_ready_state(tmp_path: Path) -> None:
    reporter = StartupReporter(tmp_path)

    reporter.starting()
    state = reporter.ready()

    restored = reporter.read()
    assert state.status == "ready"
    assert restored is not None
    assert restored.status == "ready"
    assert restored.detail == "Painel residente iniciado."


def test_startup_report_keeps_exception_type_without_traceback(tmp_path: Path) -> None:
    reporter = StartupReporter(tmp_path)

    reporter.failed(RuntimeError("componente indisponível"))

    restored = reporter.read()
    assert restored is not None
    assert restored.status == "failed"
    assert restored.detail == "RuntimeError: componente indisponível"
