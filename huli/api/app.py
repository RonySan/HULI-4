"""API HTTP autenticada da Huli."""

from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from huli import __app_name__, __version__
from huli.bootstrap import HuliRuntime, build_runtime
from huli.core import InvalidKernelInput
from huli.security import AuthenticatedUser, AuthenticationError, JournalVaultError

_bearer = HTTPBearer(auto_error=False)


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
        if resolved_runtime.auth.has_users():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A identidade proprietária da Huli já foi configurada.")
        try:
            user = resolved_runtime.auth.create_owner(payload.username, payload.password)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        return {"id": user.id, "username": user.username, "password_protected": bool(payload.password)}

    @app.post("/v1/auth/login")
    def login(payload: LoginRequest) -> dict[str, object]:
        try:
            user, token = resolved_runtime.auth.authenticate(payload.username, payload.password)
        except JournalVaultError as exc:
            raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=str(exc)) from exc
        except (AuthenticationError, ValueError) as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário ou senha inválidos.") from exc
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
        try:
            resolved_runtime.security.validate_input(payload.text)
            response = resolved_runtime.kernel.process(payload.text, metadata={"session_id": session_id, "username": user.username, "role": "owner"})
        except (InvalidKernelInput, ValueError) as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        return {"request_id": response.request_id, "session_id": session_id, "text": response.text, "handled_by": response.handled_by, "ok": response.ok}

    return app
