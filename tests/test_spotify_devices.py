"""Regressões da alpha.18: Spotify Connect e seleção segura do dispositivo."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from huli.api import create_app
from huli.brain import IntentEngine
from huli.bootstrap import build_runtime
from huli.infrastructure import Settings
from huli.integrations import spotify
from huli.integrations.spotify import SpotifyClient, SpotifyError
from huli.skills.spotify_skill import SpotifySkill


class DeviceClient:
    def __init__(self):
        self.available = [
            {"id": "notebook123", "name": "Notebook Rony", "active": False, "restricted": False},
            {"id": "celular123", "name": "Celular Rony", "active": True, "restricted": False},
            {"id": "tvrestrito123", "name": "TV Sala", "active": False, "restricted": True},
        ]
        self.calls = []

    def devices(self):
        return self.available

    def play_playlist(self, name, **kwargs):
        self.calls.append(("play", name, kwargs))
        return "Rock"

    def pause(self, **kwargs):
        self.calls.append(("pause", kwargs))

    def resume(self, **kwargs):
        self.calls.append(("resume", kwargs))

    def next(self, **kwargs):
        self.calls.append(("next", kwargs))

    def playlists(self):
        return [{"name": "Rock"}]


@pytest.mark.parametrize(("spoken", "intent"), [
    ("Huli, quais dispositivos do Spotify?", "spotify.device.list"),
    ("dispositivos Spotify", "spotify.device.list"),
    ("Huli, usar Spotify no Notebook Rony", "spotify.device.select"),
    ("spotify selecionar dispositivo Celular Rony", "spotify.device.select"),
    ("Huli, Spotify modo automático", "spotify.device.reset"),
    ("Huli, toque minha playlist Rock", "spotify.play"),
])
def test_spoken_device_intents(spoken, intent):
    assert IntentEngine().classify(spoken).intent.value == intent


def test_spotify_device_listing_is_sanitized(tmp_path, monkeypatch):
    client = SpotifyClient("a" * 32, tmp_path / "not-used", store=object())
    monkeypatch.setattr(client, "_access_token", lambda: "fake")
    monkeypatch.setattr(spotify, "_http_json", lambda url, **kwargs: {
        "devices": [
            {"id": "laptop123", "name": " Notebook ", "type": "Computer",
             "is_active": True, "is_restricted": False},
            {"id": None, "name": "no id"},
            {"id": "bad?id", "name": "bad"},
            {"id": "restricted99", "name": "TV", "is_restricted": True},
        ]
    })
    assert client.devices() == [
        {"id": "laptop123", "name": "Notebook", "type": "Computer",
         "active": True, "restricted": False},
        {"id": "restricted99", "name": "TV", "type": "", "active": False,
         "restricted": True},
    ]


def test_invalid_device_is_never_used_in_player_url():
    with pytest.raises(SpotifyError, match="inválido"):
        SpotifyClient._player_url("play", "abc?device_id=steal")
    assert SpotifyClient._player_url("pause", "notebook123").endswith(
        "/me/player/pause?device_id=notebook123"
    )


def test_selects_device_by_name_and_targets_music(tmp_path):
    from huli.core.contracts import KernelRequest

    client = DeviceClient()
    skill = SpotifySkill(Settings(data_dir=tmp_path), client=client)
    def send(text, intent):
        return skill.handle(KernelRequest(text=text, metadata={"intent": intent}))

    r = send("Huli, quais dispositivos do Spotify?", "spotify.device.list")
    assert r.ok and "Notebook Rony" in r.text
    assert "TV Sala (restrito)" in r.text
    r = send("Huli, usar Spotify no Notebook Rony", "spotify.device.select")
    assert r.ok and "não foi iniciada" in r.text
    assert not client.calls
    r = send("Huli, toque minha playlist Rock", "spotify.play")
    assert r.ok
    assert client.calls == [("play", "rock", {"device_id": "notebook123"})]
    send("pause a música", "spotify.pause")
    assert client.calls[-1] == ("pause", {"device_id": "notebook123"})
    send("Huli, Spotify modo automático", "spotify.device.reset")
    send("continue a música", "spotify.resume")
    assert client.calls[-1] == ("resume", {})


def test_restrict_ambiguous_and_disappearing_devices(tmp_path):
    from huli.core.contracts import KernelRequest

    client = DeviceClient()
    skill = SpotifySkill(Settings(data_dir=tmp_path), client=client)
    def send(text, intent):
        return skill.handle(KernelRequest(text=text, metadata={"intent": intent}))

    client.available.append(
        {"id": "notebook456", "name": "Notebook Trabalho", "active": False, "restricted": False}
    )
    assert not send("usar Spotify no Notebook", "spotify.device.select").ok
    assert not send("usar Spotify no TV Sala", "spotify.device.select").ok
    assert send("usar Spotify no Notebook Rony", "spotify.device.select").ok
    client.available = [d for d in client.available if d["id"] != "notebook123"]
    result = send("próxima faixa", "spotify.next")
    assert result.ok is False and "não está disponível" in result.text
    assert client.calls == []


def test_private_api_device_commands_require_authentication(tmp_path: Path):
    runtime = build_runtime(Settings(environment="test", log_level="CRITICAL",
                                    data_dir=tmp_path, remote_access_enabled=True))
    runtime.auth.create_owner("rony", "senha-bem-segura")
    spotify_skill = runtime.skills.resolve_intent("spotify.device.list")
    spotify_skill._client = DeviceClient()
    client = TestClient(create_app(runtime))
    assert client.post("/v1/messages", json={"text": "quais dispositivos do Spotify"}).status_code == 401
    login = client.post("/v1/auth/login", json={
        "username": "rony", "password": "senha-bem-segura"
    })
    headers = {"Authorization": "Bearer " + login.json()["access_token"]}
    listing = client.post("/v1/messages", json={
        "text": "quais dispositivos do Spotify"
    }, headers=headers)
    assert listing.status_code == 200
    assert "Notebook Rony" in listing.json()["text"]
    selection = client.post("/v1/messages", json={
        "text": "usar Spotify no Notebook Rony"
    }, headers=headers)
    assert selection.status_code == 200
    assert selection.json()["ok"] is True
    assert client.post("/v1/messages", json={"text": "abrir Chrome"}, headers=headers).status_code == 403
