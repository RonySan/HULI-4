"""Validação automatizada e isolada da fundação da Huli 4."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from huli import __app_name__, __version__
from huli.api import create_app
from huli.bootstrap import build_runtime
from huli.infrastructure import Settings


class ValidationFailure(RuntimeError):
    """Falha em um requisito obrigatório da Fase 0."""


def require(condition: bool, message: str) -> None:
    """Interrompe a validação quando um requisito não é atendido."""
    if not condition:
        raise ValidationFailure(message)


def run_validation() -> None:
    """Executa o fluxo essencial da Fase 0 sem tocar no banco real do usuário."""
    print(f"Validando {__app_name__} {__version__}...")

    with TemporaryDirectory(prefix="huli-phase0-") as temp_dir:
        data_dir = Path(temp_dir) / "data"
        settings = Settings(
            environment="validation",
            log_level="CRITICAL",
            data_dir=data_dir,
            session_hours=1,
            max_input_chars=10_000,
        )
        runtime = build_runtime(settings)

        require(runtime.database.schema_version() == 2, "Schema SQLite inesperado.")
        require(runtime.database.path.exists(), "Banco SQLite não foi criado.")
        require(runtime.skills.names == ("foundation",), "Skill Registry inesperado.")

        owner = runtime.auth.create_owner("validation-owner")
        require(owner.username == "validation-owner", "Proprietário não foi criado.")
        require(
            runtime.auth.requires_password("validation-owner") is False,
            "Proprietário sem senha foi marcado como protegido por senha.",
        )

        authenticated_user, token = runtime.auth.authenticate("validation-owner")
        require(authenticated_user.id == owner.id, "Login sem senha retornou usuário incorreto.")
        require(bool(token), "Login não retornou token.")
        require(runtime.auth.validate_token(token).id == owner.id, "Token não foi validado.")

        require(runtime.security.guest_can_execute("ping"), "Visitante não pode usar ping.")
        require(
            not runtime.security.guest_can_execute("mostrar minhas memórias"),
            "Visitante recebeu permissão para capacidade privada.",
        )

        kernel_response = runtime.kernel.process("ping")
        require(kernel_response.ok, "Kernel retornou falha para ping.")
        require(kernel_response.handled_by == "foundation", "Ping não foi tratado pela FoundationSkill.")

        latest = runtime.interactions.latest(1)
        require(bool(latest), "Interação do Kernel não foi persistida.")
        require(latest[0].user_text == "ping", "Texto do usuário não foi persistido corretamente.")
        require(
            latest[0].response_text == kernel_response.text,
            "Texto da resposta não foi persistido corretamente.",
        )

        client = TestClient(create_app(runtime))

        health = client.get("/health")
        require(health.status_code == 200, "/health não respondeu 200.")
        require(health.json()["version"] == __version__, "/health retornou versão incorreta.")

        unauthorized = client.post("/v1/messages", json={"text": "ping"})
        require(unauthorized.status_code == 401, "Rota protegida aceitou requisição sem token.")

        login = client.post(
            "/v1/auth/login",
            json={"username": "validation-owner"},
        )
        require(login.status_code == 200, "Login HTTP sem senha falhou.")
        api_token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {api_token}"}

        me = client.get("/v1/me", headers=headers)
        require(me.status_code == 200, "/v1/me falhou com token válido.")
        require(me.json()["username"] == "validation-owner", "/v1/me retornou usuário incorreto.")

        message = client.post("/v1/messages", headers=headers, json={"text": "ping"})
        require(message.status_code == 200, "/v1/messages falhou com token válido.")
        require(message.json()["handled_by"] == "foundation", "API não roteou para a Skill correta.")

        logout = client.post("/v1/auth/logout", headers=headers)
        require(logout.status_code == 204, "Logout HTTP falhou.")

        revoked = client.get("/v1/me", headers=headers)
        require(revoked.status_code == 401, "Token continuou válido após logout.")

    print("FASE 0: validação automatizada concluída com sucesso.")


def main() -> int:
    try:
        run_validation()
    except Exception as exc:
        print(f"FASE 0: FALHA - {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
