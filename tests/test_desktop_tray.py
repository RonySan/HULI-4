"""Testes do adaptador de bandeja sem abrir interface gráfica."""

from huli.desktop.tray import ResidentTray


def test_tray_dispatches_callback_through_ui_scheduler() -> None:
    scheduled = []
    calls = []
    tray = ResidentTray(
        schedule=scheduled.append,
        on_show=lambda: calls.append("show"),
        on_toggle_wake=lambda: calls.append("wake"),
        on_exit=lambda: calls.append("exit"),
        wake_enabled=lambda: False,
    )

    callback = tray._dispatch(lambda: calls.append("done"))
    callback(None, None)

    assert len(scheduled) == 1
    scheduled[0]()
    assert calls == ["done"]
