"""Skill de reprodução local e favoritos do Spotify."""

from __future__ import annotations

from huli.core.contracts import KernelRequest, KernelResponse
from huli.infrastructure.media import MediaControlError, WindowsMediaController


class MediaSkill:
    name = "media"
    intents = (
        "media.favorites",
        "media.play",
        "media.pause",
        "media.stop",
        "media.next",
        "media.previous",
    )

    def __init__(self, controller: WindowsMediaController) -> None:
        self.controller = controller

    def can_handle(self, request: KernelRequest) -> bool:
        return str(request.metadata.get("intent") or "") in self.intents

    def handle(self, request: KernelRequest) -> KernelResponse:
        intent = str(request.metadata.get("intent") or "")
        actions = {
            "media.favorites": (
                self.controller.play_favorites,
                "Abrindo suas músicas favoritas no Spotify.",
            ),
            "media.play": (self.controller.play, "Continuando a música."),
            "media.pause": (self.controller.pause, "Música pausada."),
            "media.stop": (self.controller.stop, "Reprodução encerrada."),
            "media.next": (self.controller.next, "Passando para a próxima música."),
            "media.previous": (
                self.controller.previous,
                "Voltando para a música anterior.",
            ),
        }
        selected = actions.get(intent)
        if selected is None:
            return self._response(request, "Comando de música não reconhecido.", ok=False)
        action, response_text = selected
        try:
            action()
        except MediaControlError as exc:
            return self._response(request, str(exc), ok=False)
        return self._response(request, response_text)

    def _response(
        self,
        request: KernelRequest,
        text: str,
        *,
        ok: bool = True,
    ) -> KernelResponse:
        return KernelResponse(
            request_id=request.request_id,
            text=text,
            handled_by=self.name,
            ok=ok,
        )


__all__ = ["MediaSkill"]
