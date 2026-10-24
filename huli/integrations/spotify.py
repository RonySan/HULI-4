"""Cliente Spotify pessoal: OAuth PKCE, tokens protegidos e playback controlado.

Não abre URLs de terceiros, não recebe endpoints livres, não executa comandos.
O token Spotify fica vinculado ao usuário Windows via DPAPI.
"""
from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import sys
import tempfile
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import ProxyHandler, Request, build_opener

from huli.brain.normalization import normalize_text
from huli.security.os_protection import OSProtectionError, WindowsDPAPIProtector

AUTHORIZE_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"
API_URL = "https://api.spotify.com/v1"
REDIRECT_URI = "http://127.0.0.1:8767/callback"
SCOPES = "playlist-read-private playlist-read-collaborative user-read-playback-state user-modify-playback-state"
_ID_RE = re.compile(r"^[A-Za-z0-9]{32}$")


class SpotifyError(RuntimeError):
    """Erro seguro exibível ao proprietário, sem revelar credenciais."""


class SpotifyDPAPIProtector(WindowsDPAPIProtector):
    _description = "HULI Spotify Authorization"
    _entropy = b"HULI Spotify OAuth PKCE v1"


class SpotifyTokenStore:
    """Tokens ficam criptografados no perfil Windows; nunca são versionados."""

    def __init__(self, path: Path, protector: object | None = None) -> None:
        if protector is None:
            if sys.platform != "win32":
                raise SpotifyError("A conexão Spotify está disponível nesta fase somente no Windows.")
            protector = SpotifyDPAPIProtector()
        self.path = Path(path)
        self.protector = protector

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            raise SpotifyError("Spotify não conectado. Execute: python tools/spotify_connect.py")
        try:
            encoded = self.path.read_bytes()
            decoded = self.protector.unprotect(encoded)
            obj = json.loads(decoded.decode("utf-8"))
        except (OSError, OSProtectionError, ValueError, UnicodeError, AttributeError) as exc:
            raise SpotifyError("Não foi possível abrir a autorização Spotify nesta conta do Windows.") from exc
        if not isinstance(obj, dict) or not obj.get("refresh_token"):
            raise SpotifyError("Autorização Spotify inválida. Conecte sua conta novamente.")
        return obj

    def save(self, tokens: dict[str, Any]) -> None:
        if not tokens.get("refresh_token") or not tokens.get("access_token"):
            raise SpotifyError("Spotify não retornou autorização completa.")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        encoded = self.protector.protect(
            json.dumps(tokens, separators=(",", ":")).encode("utf-8")
        )
        temporary: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                prefix=".spotify-", dir=self.path.parent, delete=False
            ) as file:
                temporary = file.name
                file.write(encoded)
                file.flush()
                os.fsync(file.fileno())
            os.chmod(temporary, 0o600)
            os.replace(temporary, self.path)
        finally:
            if temporary and os.path.exists(temporary):
                os.unlink(temporary)

    def disconnect(self) -> None:
        self.path.unlink(missing_ok=True)


def generate_pkce() -> tuple[str, str, str]:
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(48)).rstrip(b"=").decode("ascii")
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode("ascii")).digest()
    ).rstrip(b"=").decode("ascii")
    state = secrets.token_urlsafe(32)
    return verifier, challenge, state


def authorization_url(client_id: str, challenge: str, state: str) -> str:
    if not _ID_RE.fullmatch(client_id):
        raise SpotifyError("Configure HULI_SPOTIFY_CLIENT_ID com o Client ID do seu aplicativo Spotify.")
    return AUTHORIZE_URL + "?" + urlencode({
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "code_challenge_method": "S256",
        "code_challenge": challenge,
        "state": state,
        "scope": SCOPES,
    })


def _http_json(url: str, *, method: str = "GET", payload: bytes | None = None,
               token: str | None = None, form: bool = False) -> Any:
    # URLs aceitas são somente prefixos fixos deste arquivo, não entrada do usuário.
    if not (url.startswith(API_URL + "/") or url == TOKEN_URL):
        raise SpotifyError("Destino Spotify não autorizado.")
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    if payload is not None:
        headers["Content-Type"] = (
            "application/x-www-form-urlencoded" if form else "application/json"
        )
    request = Request(url, headers=headers, method=method, data=payload)
    try:
        with build_opener(ProxyHandler({})).open(request, timeout=12) as response:
            data = response.read(524289)
            status_code = response.status
    except HTTPError as exc:
        if exc.code == 401:
            raise SpotifyError("Autorização Spotify expirada ou revogada. Conecte sua conta novamente.") from exc
        if exc.code == 403:
            raise SpotifyError("Spotify recusou o controle. Confirme assinatura Premium e permissões.") from exc
        if exc.code == 404:
            raise SpotifyError("Abra o aplicativo Spotify em um dispositivo para ativar a reprodução.") from exc
        if exc.code == 429:
            raise SpotifyError("Spotify limitou as solicitações. Aguarde alguns instantes.") from exc
        raise SpotifyError(f"Spotify indisponível (HTTP {exc.code}).") from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise SpotifyError("Não consegui acessar o Spotify. Verifique a conexão.") from exc
    if status_code == 204:
        return None
    if len(data) > 524288:
        raise SpotifyError("Spotify retornou uma resposta grande demais.")
    try:
        return json.loads(data.decode("utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise SpotifyError("Spotify enviou uma resposta inválida.") from exc


class SpotifyClient:
    def __init__(self, client_id: str, token_file: Path,
                 store: SpotifyTokenStore | None = None) -> None:
        if not _ID_RE.fullmatch(client_id):
            raise SpotifyError("Configure HULI_SPOTIFY_CLIENT_ID antes de usar Spotify.")
        self.client_id = client_id
        self.store = store if store is not None else SpotifyTokenStore(token_file)

    def exchange_code(self, code: str, verifier: str) -> None:
        response = _http_json(
            TOKEN_URL, method="POST", form=True,
            payload=urlencode({
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": REDIRECT_URI,
                "client_id": self.client_id,
                "code_verifier": verifier,
            }).encode("ascii"),
        )
        self._save_token_response(response)

    def _save_token_response(self, response: object, prior: dict | None = None) -> None:
        if not isinstance(response, dict) or not response.get("access_token"):
            raise SpotifyError("Spotify não retornou o token de acesso.")
        refresh = response.get("refresh_token") or (prior or {}).get("refresh_token")
        if not refresh:
            raise SpotifyError("Spotify não retornou token de renovação.")
        expires = response.get("expires_in", 3600)
        if not isinstance(expires, int) or expires < 1:
            raise SpotifyError("Prazo de autorização Spotify inválido.")
        self.store.save({
            "access_token": response["access_token"],
            "refresh_token": refresh,
            "expires_at": (
                datetime.now(timezone.utc) + timedelta(seconds=max(0, expires - 60))
            ).timestamp(),
        })

    def _access_token(self) -> str:
        tokens = self.store.load()
        if tokens.get("access_token") and float(tokens.get("expires_at", 0)) > datetime.now(timezone.utc).timestamp():
            return str(tokens["access_token"])
        response = _http_json(
            TOKEN_URL, method="POST", form=True,
            payload=urlencode({
                "grant_type": "refresh_token",
                "refresh_token": tokens["refresh_token"],
                "client_id": self.client_id,
            }).encode("ascii"),
        )
        self._save_token_response(response, tokens)
        return self.store.load()["access_token"]

    def playlists(self) -> list[dict[str, str]]:
        items: list[dict[str, str]] = []
        for offset in range(0, 250, 50):
            response = _http_json(
                API_URL + f"/me/playlists?limit=50&offset={offset}",
                token=self._access_token(),
            )
            if not isinstance(response, dict):
                raise SpotifyError("Não foi possível consultar suas playlists.")
            entries = response.get("items")
            if not isinstance(entries, list):
                raise SpotifyError("Spotify retornou uma lista de playlists inválida.")
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                uri, name = entry.get("uri"), entry.get("name")
                if isinstance(uri, str) and re.fullmatch(r"spotify:playlist:[A-Za-z0-9]+", uri) and isinstance(name, str):
                    items.append({"name": name[:100], "uri": uri})
            if not response.get("next") or len(entries) < 50:
                break
        return items

    def play_playlist(self, name: str) -> str:
        query = normalize_text(name)
        if not query:
            raise SpotifyError("Qual playlist devo tocar? Diga: Huli, toque minha playlist Nome.")
        playlists = self.playlists()
        exact = [x for x in playlists if normalize_text(x["name"]) == query]
        matches = exact or [x for x in playlists if query in normalize_text(x["name"])]
        if not matches:
            raise SpotifyError(f"Não encontrei a playlist '{name}' nas suas playlists.")
        if len(matches) > 1:
            suggestions = ", ".join(x["name"] for x in matches[:4])
            raise SpotifyError(f"Há mais de uma playlist correspondente: {suggestions}. Diga o nome completo.")
        selected = matches[0]
        _http_json(API_URL + "/me/player/play", method="PUT",
                   token=self._access_token(),
                   payload=json.dumps({"context_uri": selected["uri"]}).encode("utf-8"))
        return selected["name"]

    def pause(self) -> None:
        _http_json(API_URL + "/me/player/pause", method="PUT",
                   token=self._access_token())

    def resume(self) -> None:
        _http_json(API_URL + "/me/player/play", method="PUT",
                   token=self._access_token())

    def next(self) -> None:
        _http_json(API_URL + "/me/player/next", method="POST",
                   token=self._access_token())
