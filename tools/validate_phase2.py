"""Validação ponta a ponta da Memory Engine 4.0."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from huli import __version__
from huli.api import create_app
from huli.bootstrap import build_runtime
from huli.infrastructure import Settings
from huli.memory import MemoryPolicyError


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def run_validation() -> None:
    print(f"Validando Memory Engine 4.0 em {__version__}...")

    with TemporaryDirectory(prefix="huli-phase2-") as temp_dir:
        runtime = build_runtime(
            Settings(
                environment="validation",
                log_level="CRITICAL",
                data_dir=Path(temp_dir) / "data",
                timezone="America/Sao_Paulo",
            )
        )
        meta = {
            "session_id": "phase2-owner",
            "username": "rony",
            "role": "owner",
        }

        require(
            runtime.database.schema_version() >= 5,
            "Schema mínimo da Fase 2 não foi aplicado.",
        )
        require("memory" in runtime.skills.names, "MemorySkill não foi registrada.")

        preference = runtime.kernel.process(
            "lembre que eu prefiro café sem açúcar",
            metadata=meta,
        )
        require(
            preference.handled_by == "memory",
            "Memória explícita não chegou à MemorySkill.",
        )
        require(
            runtime.memory_repository.count_active("rony") == 1,
            "Memória não foi persistida.",
        )

        recalled = runtime.kernel.process(
            "o que você lembra sobre café?",
            metadata=meta,
        )
        require(
            "café sem açúcar" in recalled.text,
            "Recall não encontrou memória persistida.",
        )

        runtime.kernel.process("vamos falar do projeto Medynx", metadata=meta)
        runtime.kernel.process(
            "lembre que a publicação depende de revisar o banco",
            metadata=meta,
        )
        project_memories = [
            memory
            for memory in runtime.memory_repository.list_active("rony")
            if memory.project == "Medynx"
        ]
        require(len(project_memories) == 1, "Memória não herdou o projeto ativo.")
        require(
            project_memories[0].kind.value == "project",
            "Memória de projeto recebeu tipo incorreto.",
        )

        runtime.memory.remember(owner="outro", content="prefiro chá verde")
        require(
            not runtime.memory.recall(owner="rony", query="chá verde"),
            "Memória de outro proprietário vazou no recall.",
        )

        try:
            runtime.memory.remember(
                owner="rony",
                content="minha senha é exemplo123",
                explicit=True,
            )
        except MemoryPolicyError:
            pass
        else:
            raise RuntimeError("A política aceitou uma senha como memória.")

        before_auto = runtime.memory_repository.count_active("rony")
        runtime.events.publish(
            "memory.candidate",
            {
                "owner": "rony",
                "content": "prefiro o modo escuro",
                "kind": "preference",
                "confidence": 0.97,
            },
        )
        require(
            runtime.memory_repository.count_active("rony") == before_auto + 1,
            "Candidato automático seguro não foi aprendido.",
        )

        runtime.events.publish(
            "memory.candidate",
            {
                "owner": "rony",
                "content": "minha senha é outraSenha123",
                "kind": "semantic",
                "confidence": 1.0,
            },
        )
        require(
            runtime.memory_repository.count_active("rony") == before_auto + 1,
            "Candidato secreto foi armazenado indevidamente.",
        )

        saved_id = runtime.memory.recall(owner="rony", query="café", limit=1)[0].id
        forgotten = runtime.kernel.process(f"esqueça {saved_id}", metadata=meta)
        require("esquecida" in forgotten.text, "Esquecimento explícito falhou.")
        require(
            not runtime.memory_repository.get(saved_id, "rony").is_active,
            "Esquecimento não foi persistido logicamente.",
        )

        runtime.auth.create_owner("api-owner", "1234")
        client = TestClient(create_app(runtime))
        login = client.post(
            "/v1/auth/login",
            json={"username": "api-owner", "password": "1234"},
        )
        require(login.status_code == 200, "Login HTTP da Fase 2 falhou.")
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        api_save = client.post(
            "/v1/messages",
            headers=headers,
            json={
                "text": "lembre que eu prefiro relatórios objetivos",
                "session_id": "phase2-api",
            },
        )
        api_recall = client.post(
            "/v1/messages",
            headers=headers,
            json={
                "text": "o que você lembra sobre relatórios?",
                "session_id": "phase2-api",
            },
        )
        require(
            api_save.status_code == 200
            and api_save.json()["handled_by"] == "memory",
            "API não salvou memória pelo cérebro comum.",
        )
        require(
            api_recall.status_code == 200
            and "relatórios objetivos" in api_recall.json()["text"],
            "API não recuperou memória pelo cérebro comum.",
        )

        require(
            not runtime.security.guest_can_execute("minhas memórias", "memory.list"),
            "Visitante recebeu acesso a memória privada.",
        )

    print("FASE 2: Memory Engine 4.0 validada com sucesso.")


def main() -> int:
    try:
        run_validation()
        return 0
    except Exception as exc:
        print(f"FASE 2: FALHA - {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
