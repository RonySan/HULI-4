"""Spotify alpha.17: parsing, criptografia, OAuth e API sem conexão externa."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from huli.brain import IntentEngine
from huli.bootstrap import build_runtime
from huli.infrastructure import Settings
from huli.integrations import spotify
from huli.integrations.spotify import (
    SpotifyClient, SpotifyError, SpotifyTokenStore,
    authorization_url, generate_pkce,
)
from huli.skills.spotify_skill import SpotifySkill


class FakeProtector:
    def protect(self, data: bytes) -> bytes:
        return b"encrypted:" + data[::-1]

    def unprotect(self, data: bytes) -> bytes:
        if not data.startswith(b"encrypted:"):
            raise ValueError("Invalid envelope")
        return data[len(b"encrypted:"):][::-1]


@pytest.fixture
def store(tmp_path: Path):
    return SpotifyTokenStore(tmp_path / "spotify_tokens.dpapi", protector=FakeProtector())


def _client(store):
    return SpotifyClient("a" * 32, store.path, store)


def test_pkce_url_is_local_and_does_not_use_client_secret():
    verifier, challenge, state = generate_pkce()
    url = authorization_url("a" * 32, challenge, state)
    assert len(verifier) >= 43 and len(state) >= 32
    assert "127.0.0.1%3A8767" in url
    assert "code_challenge_method=S256" in url
    assert "state=" in url
    assert "client_secret" not in url
    with pytest.raises(SpotifyError):
        authorization_url("invalid", challenge, state)


def test_token_store_is_encrypted_and_restricted(tmp_path, store):
    tokens = {"access_token": "access-test", "refresh_token": "refresh-test", "expires_at": 1}
    store.save(tokens)
    raw = store.path.read_bytes()
    assert b"access-test" not in raw and b"refresh-test" not in raw
    assert store.load() == tokens
    store.path.write_bytes(b"wrong")
    with pytest.raises(SpotifyError):
        store.load()


def test_spotify_client_refreshes_and_rotates_token(store, monkeypatch):
    store.save({"access_token": "expired", "refresh_token": "old-refresh", "expires_at": 1})
    def fake_http(url, **kwargs):
        assert url == spotify.TOKEN_URL
        assert kwargs["form"] is True
        return {"access_token": "fresh", "refresh_token": "new-refresh", "expires_in": 3600}
    monkeypatch.setattr(spotify, "_http_json", fake_http)
    assert _client(store)._access_token() == "fresh"
    assert store.load()["refresh_token"] == "new-refresh"


def test_play_exact_playlist_without_mistaking_name(store, monkeypatch):
    client = _client(store)
    store.save({"access_token": "t", "refresh_token": "r", "expires_at": 9999999999})
    client.playlists = lambda: [
        {"name": "Rock", "uri": "spotify:playlist:rockID"},
        {"name": "Rock Antigo", "uri": "spotify:playlist:oldID"},
    ]
    calls = []
    monkeypatch.setattr(spotify, "_http_json", lambda url, **kw: calls.append((url, kw)))
    assert client.play_playlist("rock") == "Rock"
    assert calls[0][0].endswith("/me/player/play")
    assert json.loads(calls[0][1]["payload"]) == {"context_uri": "spotify:playlist:rockID"}
    with pytest.raises(SpotifyError, match="mais de uma playlist"):
        client.play_playlist("ro")
    assert len(calls) == 1


def test_playlist_requires_name_not_arbitrary_first(store):
    client = _client(store)
    with pytest.raises(SpotifyError, match="Qual playlist"):
        client.play_playlist("")


@pytest.mark.parametrize(("message", "expected"), [
    ("Huli, toque minha playlist Rock", "spotify.play"),
    ("tocar playlist de Linkin Park", "spotify.play"),
    ("pause a música", "spotify.pause"),
    ("continue a música", "spotify.resume"),
    ("tocar Spotify", "spotify.resume"),
    ("próxima faixa", "spotify.next"),
    ("quais são minhas playlists", "spotify.list"),
    ("abrir o Google Chrome", "app.open"),
])
def test_classify_spotify_without_breaking_existing_commands(message, expected):
    assert IntentEngine().classify(message).intent.value == expected


class FakeClient:
    def __init__(self):
        self.calls = []
    def play_playlist(self, name):
        self.calls.append(("play", name))
        return "Rock"
    def pause(self):
        self.calls.append(("pause",))
    def resume(self):
        self.calls.append(("resume",))
    def next(self):
        self.calls.append(("next",))
    def playlists(self):
        return [{"name": "Rock"}]


def test_spotify_skill_routes_precisely(tmp_path):
    from huli.core.contracts import KernelRequest
    fake = FakeClient()
    skill = SpotifySkill(Settings(data_dir=tmp_path), client=fake)
    for message, intent in [
        ("Huli, toque minha playlist Rock", "spotify.play"),
        ("pause a música", "spotify.pause"),
        ("continue a música", "spotify.resume"),
        ("próxima faixa", "spotify.next"),
        ("quais são minhas playlists", "spotify.list"),
    ]:
        req = KernelRequest(text=message, metadata={"intent": intent})
        response = skill.handle(req)
        assert response.ok is True and response.handled_by == "spotify"
    assert fake.calls == [
        ("play", "rock"), ("pause",), ("resume",), ("next",),
    ]


def test_ollama_cannot_intercept_spotify_commands(tmp_path):
    runtime = build_runtime(Settings(environment="test", log_level="CRITICAL",
                                     data_dir=tmp_path, llm_enabled=True))
    response = runtime.kernel.process("Huli, toque minha playlist Rock")
    assert response.handled_by == "spotify"
    assert response.ok is False
    assert "HULI_SPOTIFY_CLIENT_ID" in response.text


def test_missing_spotify_access_stays_graceful(tmp_path):
    runtime = build_runtime(Settings(environment="test", log_level="CRITICAL",
                                     data_dir=tmp_path))
    response = runtime.kernel.process("pause a música")
    assert response.handled_by == "spotify" and response.ok is False
