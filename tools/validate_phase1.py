"""Validação ponta a ponta do cérebro básico da Fase 1."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from huli import __version__
from huli.api import create_app
from huli.bootstrap import build_runtime
from huli.infrastructure import Settings


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def run_validation() -> None:
    print(f"Validando Fase 1 em {__version__}...")

    with TemporaryDirectory(prefix="huli-phase1-") as temp_dir:
        runtime = build_runtime(
            Settings(
                environment="validation",
                log_level="CRITICAL",
                data_dir=Path(temp_dir) / "data",
                timezone="America/Sao_Paulo",
            )
        )
        meta = {
            "session_id": "phase1",
            "username": "rony",
            "role": "owner",
        }

        require(
            runtime.database.schema_version() >= 4,
            "Schema mínimo da Fase 1 não foi aplicado.",
        )
        require(
            runtime.kernel.process("oi huli, bom dia", metadata=meta).handled_by
            == "smalltalk",
            "Small Talk falhou.",
        )
        require(
            runtime.kernel.process(
                "vamos falar do projeto Medynx",
                metadata=meta,
            ).handled_by
            == "project-context",
            "Project Context falhou.",
        )
        require(
            runtime.context.snapshot("phase1").active_project == "Medynx",
            "Projeto ativo não foi salvo no contexto.",
        )
        require(
            runtime.kernel.process(
                "adiciona uma tarefa revisar o banco prioridade alta",
                metadata=meta,
            ).handled_by
            == "planner",
            "Planner falhou.",
        )

        pending = runtime.tasks.list_pending(project="Medynx")
        require(
            len(pending) == 1 and pending[0].priority == "alta",
            "Tarefa não herdou projeto/prioridade.",
        )
        require(
            runtime.kernel.process(
                "agenda dentista amanhã às 15:00",
                metadata=meta,
            ).handled_by
            == "agenda",
            "Agenda falhou.",
        )
        require(
            len(runtime.agenda.upcoming(limit=10)) == 1,
            "Compromisso não foi persistido.",
        )
        require(
            runtime.kernel.process("resumo do dia", metadata=meta).handled_by
            == "daily-summary",
            "Resumo diário falhou.",
        )
        require(
            "concluída"
            in runtime.kernel.process(
                f"concluir tarefa {pending[0].id}",
                metadata=meta,
            ).text,
            "Conclusão de tarefa falhou.",
        )
        require(
            runtime.kernel.process("que horas são?", metadata=meta).handled_by
            == "time",
            "Horário falhou.",
        )

        runtime.auth.create_owner("api-owner", "senha-1234")
        client = TestClient(create_app(runtime))
        login = client.post(
            "/v1/auth/login",
            json={"username": "api-owner", "password": "senha-1234"},
        )
        require(login.status_code == 200, "Login da API falhou.")

        headers = {
            "Authorization": f"Bearer {login.json()['access_token']}"
        }
        api_message = client.post(
            "/v1/messages",
            headers=headers,
            json={"text": "oi Huli", "session_id": "mobile-test"},
        )
        require(
            api_message.status_code == 200
            and api_message.json()["handled_by"] == "smalltalk",
            "API não usou o mesmo cérebro.",
        )
        require(
            api_message.json()["session_id"] == "mobile-test",
            "API perdeu session_id.",
        )

    print("FASE 1: validação automatizada concluída com sucesso.")


def main() -> int:
    try:
        run_validation()
        return 0
    except Exception as exc:
        print(f"FASE 1: FALHA - {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
