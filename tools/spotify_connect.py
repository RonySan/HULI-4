"""Conecta o Spotify à Huli em um navegador no PC Windows, via OAuth PKCE."""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlsplit
import secrets
import sys
import webbrowser

from huli.infrastructure import load_settings
from huli.integrations.spotify import (
    REDIRECT_URI, SpotifyClient, SpotifyError, authorization_url, generate_pkce,
)


def main() -> int:
    settings = load_settings()
    if sys.platform != "win32":
        print("Esta conexão Spotify exige Windows e proteção DPAPI.")
        return 1
    try:
        client = SpotifyClient(settings.spotify_client_id,
                               settings.data_dir / "spotify_tokens.dpapi")
        verifier, challenge, state = generate_pkce()
        authorize = authorization_url(settings.spotify_client_id, challenge, state)
    except SpotifyError as exc:
        print(f"Huli: {exc}")
        return 1

    result: dict[str, str] = {}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            # O código OAuth não deve aparecer no terminal nem nos logs.
            pass

        def do_GET(self):
            parsed = urlsplit(self.path)
            if parsed.path != "/callback":
                self.send_error(404)
                return
            query = parse_qs(parsed.query)
            expected = query.get("state", [])
            if len(expected) != 1 or not secrets.compare_digest(expected[0], state):
                self.send_error(400, "Estado OAuth inválido")
                return
            if query.get("error"):
                result["error"] = "Autorização não concedida."
            else:
                code = query.get("code", [])
                if len(code) != 1 or not code[0]:
                    result["error"] = "Spotify não retornou um código válido."
                else:
                    result["code"] = code[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Referrer-Policy", "no-referrer")
            self.end_headers()
            self.wfile.write(
                b"<html><body><h2>Huli - Spotify</h2>"
                b"<p>Autorizacao recebida. Pode fechar esta janela.</p></body></html>"
            )

    with HTTPServer(("127.0.0.1", 8767), Handler) as server:
        server.timeout = 180
        print("Conectando Spotify. A página de autorização será aberta no navegador.")
        if not webbrowser.open(authorize):
            print(f"Abra o endereço no navegador:\n{authorize}")
        server.handle_request()
    if "error" in result:
        print("Huli:", result["error"])
        return 1
    if "code" not in result:
        print("Huli: tempo esgotado ou autorização não recebida.")
        return 1
    try:
        client.exchange_code(result["code"], verifier)
    except SpotifyError as exc:
        print(f"Huli: {exc}")
        return 1
    print("Huli: conta Spotify conectada nesta conta do Windows.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
