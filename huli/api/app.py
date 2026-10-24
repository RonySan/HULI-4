"""API HTTP autenticada da Huli."""

from __future__ import annotations

from pathlib import Path
from collections import deque
from threading import Lock
from time import monotonic

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from huli import __app_name__, __version__
from huli.bootstrap import HuliRuntime, build_runtime
from huli.core import InvalidKernelInput
from huli.security import AuthenticatedUser, AuthenticationError, JournalVaultError
from huli.security.remote import remote_intent_allowed

_bearer = HTTPBearer(auto_error=False)
_WEB_ROOT = Path(__file__).resolve().parents[1] / "web"

class SetupRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(default="", max_length=256)


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(default="", max_length=256)


class MessageRequest(BaseModel):
    text: str = Field(min_length=1)
    session_id: str | None = Field(default=None, max_length=128)


def create_app(runtime: HuliRuntime | None = None) -> FastAPI:
    resolved_runtime = runtime or build_runtime()
    app = FastAPI(title="Huli API", version=__version__, docs_url="/docs", redoc_url=None)
    app.state.runtime = resolved_runtime
    failed_logins: dict[str, deque[float]] = {}
    login_lock = Lock()

    @app.middleware("http")
    async def private_cache_headers(request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/v1/"):
            response.headers["Cache-Control"] = "no-store"
            response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    app.mount("/app/static", StaticFiles(directory=_WEB_ROOT), name="huli-web")

    @app.get("/app", include_in_schema=False)
    def web_client() -> FileResponse:
        return FileResponse(
            _WEB_ROOT / "index.html",
            media_type="text/html; charset=utf-8",
            headers={
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff",
                "Referrer-Policy": "no-referrer",
                "Content-Security-Policy": "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; manifest-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'",
            },
        )

    def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> AuthenticatedUser:
        if credentials is None or credentials.scheme.lower() != "bearer":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Autenticação necessária.")
        try:
            return resolved_runtime.auth.validate_token(credentials.credentials)
        except AuthenticationError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    def bearer_token(credentials: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> str:
        if credentials is None or credentials.scheme.lower() != "bearer":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Autenticação necessária.")
        return credentials.credentials

    @app.get("/health")
    def health() -> dict[str, object]:
        return {"app": __app_name__, "version": __version__, "status": "ok", "environment": resolved_runtime.settings.environment, "schema_version": resolved_runtime.database.schema_version(), "skills": resolved_runtime.skills.names}

    @app.post("/v1/auth/setup", status_code=status.HTTP_201_CREATED)
    def setup(payload: SetupRequest) -> dict[str, object]:
        if resolved_runtime.settings.remote_access_enabled:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Configure o proprietário localmente antes de habilitar o acesso privado.",
            )
        if resolved_runtime.auth.has_users():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A identidade proprietária da Huli já foi configurada.")
        try:
            user = resolved_runtime.auth.create_owner(payload.username, payload.password)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        return {"id": user.id, "username": user.username, "password_protected": bool(payload.password)}

    @app.post("/v1/auth/login")
    def login(payload: LoginRequest, request: Request) -> dict[str, object]:
        client_ip = request.client.host if request.client else "unknown"
        if resolved_runtime.settings.remote_access_enabled:
            with login_lock:
                now = monotonic()
                attempts = failed_logins.setdefault(client_ip, deque())
                while attempts and now - attempts[0] > 300:
                    attempts.popleft()
                if len(attempts) >= 6:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Muitas tentativas. Aguarde cinco minutos.",
                    )
            if len(payload.password) < resolved_runtime.security.min_password_length:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Acesso privado exige senha de pelo menos oito caracteres.",
                )
        if resolved_runtime.settings.remote_access_enabled and not payload.password:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso privado exige uma conta protegida por senha.",
            )
        try:
            user, token = resolved_runtime.auth.authenticate(payload.username, payload.password)
        except JournalVaultError as exc:
            raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=str(exc)) from exc
        except (AuthenticationError, ValueError) as exc:
            if resolved_runtime.settings.remote_access_enabled:
                with login_lock:
                    failed_logins.setdefault(client_ip, deque()).append(monotonic())
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário ou senha inválidos.") from exc
        if resolved_runtime.settings.remote_access_enabled:
            with login_lock:
                failed_logins.pop(client_ip, None)
        unlock_result = resolved_runtime.journal_vault.last_unlock_result(user.username)
        return {"token_type": "bearer", "access_token": token, "user": {"id": user.id, "username": user.username}, "password_upgrade_recommended": bool(payload.password) and len(payload.password) < resolved_runtime.security.min_password_length, "journal_vault": {"migrated_entries": unlock_result.migrated_entries if unlock_result else 0, "migration_backup": str(unlock_result.migration_backup) if unlock_result and unlock_result.migration_backup else None, "os_protection": unlock_result.os_protection if unlock_result else None}}

    @app.get("/v1/me")
    def me(user: AuthenticatedUser = Depends(current_user)) -> dict[str, object]:
        return {"id": user.id, "username": user.username}

    @app.post("/v1/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
    def logout(_user: AuthenticatedUser = Depends(current_user), token: str = Depends(bearer_token)) -> None:
        resolved_runtime.auth.revoke_token(token)

    @app.post("/v1/messages")
    def messages(payload: MessageRequest, user: AuthenticatedUser = Depends(current_user)) -> dict[str, object]:
        session_id = payload.session_id or f"api-user-{user.id}"
        if resolved_runtime.settings.remote_access_enabled:
            intent = resolved_runtime.intents.classify(payload.text).intent.value
            if not remote_intent_allowed(intent):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Esse comando está disponível apenas no computador local.",
                )
        try:
            resolved_runtime.security.validate_input(payload.text)
            response = resolved_runtime.kernel.process(payload.text, metadata={"session_id": session_id, "username": user.username, "role": "owner", "remote_client": resolved_runtime.settings.remote_access_enabled})
            if response.handled_by == "remote-security":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Esse comando está disponível apenas no computador local.",
                )
        except (InvalidKernelInput, ValueError) as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        return {"request_id": response.request_id, "session_id": session_id, "text": response.text, "handled_by": response.handled_by, "ok": response.ok}

    return app
