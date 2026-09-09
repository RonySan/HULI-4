"""Ícone da Huli na bandeja do Windows."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


class TrayUnavailableError(RuntimeError):
    """O modo de bandeja não pode ser iniciado nesta instalação."""


class ResidentTray:
    """Adapta o pystray sem acoplar suas threads ao Tkinter."""

    def __init__(
        self,
        *,
        schedule: Callable[[Callable[[], None]], None],
        on_show: Callable[[], None],
        on_toggle_wake: Callable[[], None],
        on_exit: Callable[[], None],
        wake_enabled: Callable[[], bool],
    ) -> None:
        self._schedule = schedule
        self._on_show = on_show
        self._on_toggle_wake = on_toggle_wake
        self._on_exit = on_exit
        self._wake_enabled = wake_enabled
        self._icon: Any | None = None
        self._status = "Huli ativa"

    @property
    def running(self) -> bool:
        return self._icon is not None

    def start(self) -> None:
        if self.running:
            return
        try:
            import pystray
            from PIL import Image, ImageDraw
        except ImportError as exc:
            raise TrayUnavailableError(
                "Instale o modo residente com INSTALAR_MODO_RESIDENTE.bat."
            ) from exc

        image = Image.new("RGBA", (64, 64), (24, 43, 68, 255))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((2, 2, 61, 61), radius=14, fill=(24, 43, 68, 255))
        draw.line((18, 15, 18, 49), fill=(108, 210, 255, 255), width=7)
        draw.line((46, 15, 46, 49), fill=(108, 210, 255, 255), width=7)
        draw.line((19, 32, 45, 32), fill=(108, 210, 255, 255), width=7)

        menu = pystray.Menu(
            pystray.MenuItem("Abrir painel", self._dispatch(self._on_show), default=True),
            pystray.MenuItem(
                "Escuta contínua",
                self._dispatch(self._on_toggle_wake),
                checked=lambda _item: self._wake_enabled(),
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Encerrar Huli", self._dispatch(self._on_exit)),
        )
        self._icon = pystray.Icon("huli", image, self._status, menu)
        try:
            self._icon.run_detached()
        except Exception as exc:
            self._icon = None
            raise TrayUnavailableError(f"Não consegui criar o ícone da Huli: {exc}") from exc

    def _dispatch(self, callback: Callable[[], None]) -> Callable[..., None]:
        def dispatched(*_args: object) -> None:
            self._schedule(callback)

        return dispatched

    def update(self, status: str) -> None:
        normalized = " ".join(status.split())[:120] or "Huli ativa"
        if normalized == self._status:
            return
        self._status = normalized
        icon = self._icon
        if icon is None:
            return
        try:
            icon.title = normalized
            icon.update_menu()
        except Exception:
            return

    def notify(self, message: str, title: str = "Huli") -> None:
        icon = self._icon
        if icon is None:
            return
        try:
            icon.notify(" ".join(message.split())[:240], title)
        except Exception:
            return

    def stop(self) -> None:
        icon, self._icon = self._icon, None
        if icon is None:
            return
        try:
            icon.stop()
        except Exception:
            return
