"""Comandos de reprodução Spotify sem delegar ações a modelos generativos."""
from __future__ import annotations

import re

from huli.brain.normalization import normalize_text
from huli.core.contracts import KernelRequest, KernelResponse
from huli.infrastructure.config import Settings
from huli.integrations.spotify import SpotifyClient, SpotifyError


class SpotifySkill:
    name = "spotify"
    intents = ("spotify.play", "spotify.pause", "spotify.resume", "spotify.next", "spotify.list")

    def __init__(self, settings: Settings, client: SpotifyClient | None = None) -> None:
        self.settings = settings
        self._client = client

    def can_handle(self, request: KernelRequest) -> bool:
        return str(request.metadata.get("intent") or "") in self.intents

    def handle(self, request: KernelRequest) -> KernelResponse:
        intent = str(request.metadata.get("intent") or "")
        if intent not in self.intents:
            return KernelResponse(request_id=request.request_id,
                                  text="Comando Spotify não autorizado.", handled_by=self.name, ok=False)
        try:
            client = self._client or SpotifyClient(
                self.settings.spotify_client_id,
                self.settings.data_dir / "spotify_tokens.dpapi",
            )
            if intent == "spotify.play":
                normalized = normalize_text(request.text)
                normalized = re.sub(r"^huli\s+", "", normalized)
                match = re.fullmatch(
                    r"(?:toque|toca|tocar|reproduza|reproduzir)\s+"
                    r"(?:(?:a |minha )?playlist(?:\s+(?:de|do|da))?)"
                    r"(?:\s+(.*))?", normalized,
                )
                if not match or not match.group(1):
                    raise SpotifyError("Diga o nome da playlist: Huli, toque minha playlist Rock.")
                name = client.play_playlist(match.group(1))
                message = f"Comando enviado ao Spotify para tocar a playlist '{name}'."
            elif intent == "spotify.pause":
                client.pause()
                message = "Comando de pausa enviado ao Spotify."
            elif intent == "spotify.resume":
                client.resume()
                message = "Comando para continuar a reprodução enviado ao Spotify."
            elif intent == "spotify.next":
                client.next()
                message = "Comando para próxima faixa enviado ao Spotify."
            else:
                playlists = client.playlists()
                names = [p["name"] for p in playlists[:12]]
                message = ("Suas playlists: " + ", ".join(names)) if names else "Nenhuma playlist encontrada."
        except SpotifyError as exc:
            return KernelResponse(request_id=request.request_id, text=str(exc),
                                  handled_by=self.name, ok=False)
        return KernelResponse(request_id=request.request_id, text=message,
                              handled_by=self.name)
