"""Controle Spotify por voz/texto: regras explícitas, sem executar ferramentas de LLM."""
from __future__ import annotations

import re
from threading import RLock

from huli.brain.normalization import normalize_text
from huli.core.contracts import KernelRequest, KernelResponse
from huli.infrastructure.config import Settings
from huli.integrations.spotify import SpotifyClient, SpotifyError


class SpotifySkill:
    name = "spotify"
    intents = (
        "spotify.play", "spotify.pause", "spotify.resume", "spotify.next", "spotify.list",
        "spotify.device.list", "spotify.device.select", "spotify.device.reset",
    )

    def __init__(self, settings: Settings, client: SpotifyClient | None = None) -> None:
        self.settings = settings
        self._client = client
        # Preferência temporária deste processo; nunca gravar ID no banco.
        self._selected_device_id: str | None = None
        self._lock = RLock()

    def can_handle(self, request: KernelRequest) -> bool:
        return str(request.metadata.get("intent") or "") in self.intents

    def _target(self, client: SpotifyClient) -> str | None:
        if not self._selected_device_id:
            return None
        # Spotify não garante que device_id seja estável. Consultar a cada ação.
        matches = [
            device for device in client.devices()
            if device["id"] == self._selected_device_id
        ]
        if not matches or matches[0]["restricted"]:
            self._selected_device_id = None
            raise SpotifyError(
                "O dispositivo selecionado não está disponível. "
                "Diga 'Huli, quais dispositivos do Spotify' para escolher novamente."
            )
        return self._selected_device_id

    def _select(self, client: SpotifyClient, raw_name: str) -> str:
        name = normalize_text(raw_name)
        if not name:
            raise SpotifyError("Informe o nome do dispositivo Spotify.")
        available = [d for d in client.devices() if not d["restricted"]]
        exact = [d for d in available if normalize_text(str(d["name"])) == name]
        matches = exact or [
            d for d in available if name in normalize_text(str(d["name"]))
        ]
        if not matches:
            raise SpotifyError(
                "Dispositivo não encontrado ou restrito. "
                "Diga 'quais dispositivos do Spotify' para consultar."
            )
        if len(matches) > 1:
            options = ", ".join(str(d["name"]) for d in matches[:5])
            raise SpotifyError(
                f"Há vários dispositivos correspondentes: {options}. "
                "Diga o nome completo."
            )
        self._selected_device_id = str(matches[0]["id"])
        return str(matches[0]["name"])

    def handle(self, request: KernelRequest) -> KernelResponse:
        with self._lock:
            return self._handle_locked(request)

    def _handle_locked(self, request: KernelRequest) -> KernelResponse:
        intent = str(request.metadata.get("intent") or "")
        if intent not in self.intents:
            return KernelResponse(
                request_id=request.request_id,
                text="Comando Spotify não autorizado.",
                handled_by=self.name, ok=False,
            )
        try:
            if intent == "spotify.device.reset":
                self._selected_device_id = None
                message = "Vou controlar o dispositivo ativo no Spotify."
            else:
                client = self._client or SpotifyClient(
                    self.settings.spotify_client_id,
                    self.settings.data_dir / "spotify_tokens.dpapi",
                )
                if intent == "spotify.device.list":
                    devices = client.devices()
                    if not devices:
                        message = "Nenhum dispositivo Spotify disponível. Abra o Spotify no celular ou computador."
                    else:
                        names = [
                            f"{d['name']} ({'restrito' if d['restricted'] else 'ativo' if d['active'] else 'disponível'})"
                            for d in devices[:12]
                        ]
                        message = "Dispositivos Spotify: " + ", ".join(names) + "."
                elif intent == "spotify.device.select":
                    normalized = normalize_text(request.text)
                    normalized = re.sub(r"^huli\s+", "", normalized)
                    match = re.fullmatch(
                        r"(?:usar spotify no|use spotify no|spotify usar dispositivo|"
                        r"spotify selecionar dispositivo|selecione dispositivo spotify)\s+(.+)",
                        normalized,
                    )
                    if not match:
                        raise SpotifyError(
                            "Diga: Huli, usar Spotify no nome do dispositivo."
                        )
                    name = self._select(client, match.group(1))
                    message = (
                        f"Selecionei {name} para os próximos comandos Spotify. "
                        "A reprodução não foi iniciada."
                    )
                elif intent == "spotify.play":
                    normalized = normalize_text(request.text)
                    normalized = re.sub(r"^huli\s+", "", normalized)
                    match = re.fullmatch(
                        r"(?:toque|toca|tocar|reproduza|reproduzir)\s+"
                        r"(?:(?:a |minha )?playlist(?:\s+(?:de|do|da))?)"
                        r"(?:\s+(.*))?", normalized,
                    )
                    if not match or not match.group(1):
                        raise SpotifyError(
                            "Diga o nome da playlist: Huli, toque minha playlist Rock."
                        )
                    target = self._target(client)
                    name = client.play_playlist(
                        match.group(1), **({"device_id": target} if target else {})
                    )
                    message = f"Comando enviado ao Spotify para tocar a playlist '{name}'."
                elif intent == "spotify.pause":
                    target = self._target(client)
                    client.pause(**({"device_id": target} if target else {}))
                    message = "Comando de pausa enviado ao Spotify."
                elif intent == "spotify.resume":
                    target = self._target(client)
                    client.resume(**({"device_id": target} if target else {}))
                    message = "Comando para continuar a reprodução enviado ao Spotify."
                elif intent == "spotify.next":
                    target = self._target(client)
                    client.next(**({"device_id": target} if target else {}))
                    message = "Comando para próxima faixa enviado ao Spotify."
                else:
                    playlists = client.playlists()
                    names = [p["name"] for p in playlists[:12]]
                    message = (
                        "Suas playlists: " + ", ".join(names)
                        if names else "Nenhuma playlist encontrada."
                    )
        except SpotifyError as exc:
            return KernelResponse(
                request_id=request.request_id, text=str(exc),
                handled_by=self.name, ok=False,
            )
        return KernelResponse(
            request_id=request.request_id,
            text=message,
            handled_by=self.name,
        )
