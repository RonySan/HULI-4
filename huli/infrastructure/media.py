"""Controles locais de mídia do Windows sem automação de shell."""

from __future__ import annotations

import ctypes
import os
import sys
import time
from typing import Callable


class MediaControlError(RuntimeError):
    """O Windows não conseguiu entregar um comando de mídia."""


class WindowsMediaController:
    """Envia comandos multimídia conhecidos e abre favoritos do Spotify."""

    _WM_APPCOMMAND = 0x0319
    _HWND_BROADCAST = 0xFFFF
    _COMMANDS = {
        "next": 11,
        "previous": 12,
        "stop": 13,
        "play_pause": 14,
        "play": 46,
        "pause": 47,
    }
    _SPOTIFY_FAVORITES = "spotify:collection:tracks"

    def __init__(
        self,
        *,
        uri_opener: Callable[[str], None] | None = None,
        command_sender: Callable[[int], None] | None = None,
        sleeper: Callable[[float], None] = time.sleep,
        platform_name: str | None = None,
    ) -> None:
        self.platform_name = platform_name or sys.platform
        self._uri_opener = uri_opener or self._startfile
        self._command_sender = command_sender or self._send_windows_command
        self._sleeper = sleeper

    def play_favorites(self) -> None:
        self._check_windows()
        try:
            self._uri_opener(self._SPOTIFY_FAVORITES)
            self._sleeper(2.0)
            self._command_sender(self._COMMANDS["play"])
        except OSError as exc:
            raise MediaControlError(
                "Não consegui abrir suas músicas favoritas no Spotify. "
                "Confirme se o aplicativo está instalado."
            ) from exc

    def play(self) -> None:
        self._send("play")

    def pause(self) -> None:
        self._send("pause")

    def stop(self) -> None:
        self._send("stop")

    def next(self) -> None:
        self._send("next")

    def previous(self) -> None:
        self._send("previous")

    def _send(self, action: str) -> None:
        self._check_windows()
        try:
            self._command_sender(self._COMMANDS[action])
        except OSError as exc:
            raise MediaControlError(
                "O Windows não conseguiu controlar a reprodução de mídia."
            ) from exc

    def _check_windows(self) -> None:
        if not self.platform_name.casefold().startswith("win"):
            raise MediaControlError(
                "Os controles locais de mídia desta versão exigem Windows."
            )

    @staticmethod
    def _startfile(uri: str) -> None:
        if uri != WindowsMediaController._SPOTIFY_FAVORITES:
            raise OSError("URI de mídia não autorizada.")
        if not hasattr(os, "startfile"):
            raise OSError("Abertura local indisponível.")
        os.startfile(uri)  # type: ignore[attr-defined]

    @classmethod
    def _send_windows_command(cls, command: int) -> None:
        result = ctypes.windll.user32.SendMessageW(
            cls._HWND_BROADCAST,
            cls._WM_APPCOMMAND,
            0,
            command << 16,
        )
        if result == 0:
            return


__all__ = ["MediaControlError", "WindowsMediaController"]
