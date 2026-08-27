"""Validação ponta a ponta do Personal Knowledge Graph em staging."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from huli import __version__
from huli.api import create_app
from huli.bootstrap import build_runtime
from huli.infrastructure import Settings
from huli.knowledge import EntityKind


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def run_validation() -> None:
    print(f"Validando Knowledge Graph staging em {__version__}...")
    with TemporaryDirectory(prefix="huli-phase3-") as temp_dir:
        runtime = build_runtime(
            Settings(
                environment="validation",
                log_level="CRITICAL",
                data_dir=Path(temp_dir) / "data",
                timezone="America/Sao_Paulo",
            )
        )
        meta = {
            "session_id": "phase3-owner",
            "username": "rony",
            "role": "owner",
        }

        require(runtime.database.schema_version() >= 6, "Schema 6 não foi aplicado.")
        require("knowledge" in runtime.skills.names, "KnowledgeSkill não foi registrada.")

        saved = runtime.kernel.process(
            "lembre que Medynx é desenvolvido pela Impulso Digital",
            metadata=meta,
        )
        require(saved.handled_by == "memory", "Relação-base não foi salva na memória.")

        developer = runtime.kernel.process("quem desenvolve Medynx?", metadata=meta)
        require(developer.handled_by == "knowledge", "Consulta não chegou ao KnowledgeSkill.")
        require("Impulso Digital" in developer.text, "Relação desenvolvido_por não foi recuperada.")

        runtime.kernel.process(
            "lembre que Medynx depende de MySQL",
            metadata=meta,
        )
        dependency = runtime.kernel.process("do que Medynx depende?", metadata=meta)
        require("MySQL" in dependency.text, "Relação depende_de não foi recuperada.")

        project = runtime.knowledge.resolve(owner="rony", query="Medynx")
        require(project.name == "Medynx", "Entidade Medynx não foi resolvida.")
        runtime.knowledge_repository.add_alias(
            owner="rony",
            entity_id=project.id,
            alias="Sistema Médico",
        )
        require(
            runtime.knowledge.resolve(owner="rony", query="Sistema Médico").id == project.id,
            "Alias não resolveu para a entidade correta.",
        )
        runtime.knowledge.add_fact(
            owner="rony",
            entity=project,
            key="status",
            value="em desenvolvimento",
        )
        description = runtime.kernel.process("o que você sabe sobre Medynx?", metadata=meta)
        require("status: em desenvolvimento" in description.text, "Fato estruturado não apareceu.")

        runtime.memory.remember(owner="outro", content="Medynx depende de PostgreSQL")
        other = runtime.knowledge.related(
            owner="outro",
            subject_query="Medynx",
            predicate="depende_de",
        )
        require(other[0].name == "PostgreSQL", "Conhecimento do segundo proprietário falhou.")
        require("PostgreSQL" not in dependency.text, "Conhecimento vazou entre proprietários.")

        unknown = runtime.kernel.process("quem desenvolve Projeto Fantasma?", metadata=meta)
        require(not unknown.ok and "Não encontrei" in unknown.text, "Consulta desconhecida fabricou resposta.")

        dependency_memory = runtime.memory.recall(owner="rony", query="MySQL", limit=1)[0]
        runtime.kernel.process(f"esqueça {dependency_memory.id}", metadata=meta)
        after_forget = runtime.kernel.process("do que Medynx depende?", metadata=meta)
        require(not after_forget.ok, "Relação derivada continuou ativa após esquecer a fonte.")
        require("MySQL" not in after_forget.text, "Conhecimento esquecido ainda foi afirmado.")

        manual_company = runtime.knowledge.ensure_entity(
            owner="rony",
            name="Empresa Exemplo",
            kind=EntityKind.COMPANY,
        )
        require(manual_company.is_active, "Entidade manual não foi criada.")

        runtime.auth.create_owner("api-owner", "senha-1234")
        client = TestClient(create_app(runtime))
        login = client.post(
            "/v1/auth/login",
            json={"username": "api-owner", "password": "senha-1234"},
        )
        require(login.status_code == 200, "Login da API falhou.")
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        api_save = client.post(
            "/v1/messages",
            headers=headers,
            json={
                "text": "lembre que Portal está hospedado no servidor Nuvem",
                "session_id": "phase3-api",
            },
        )
        api_query = client.post(
            "/v1/messages",
            headers=headers,
            json={
                "text": "qual servidor hospeda Portal?",
                "session_id": "phase3-api",
            },
        )
        require(api_save.status_code == 200, "API não salvou a memória-base.")
        require(
            api_query.status_code == 200
            and api_query.json()["handled_by"] == "knowledge"
            and "servidor Nuvem" in api_query.json()["text"],
            "API não consultou o mesmo Knowledge Graph.",
        )

        require(
            not runtime.security.guest_can_execute(
                "o que você sabe sobre Medynx?",
                "knowledge.describe",
            ),
            "Visitante recebeu acesso ao Knowledge Graph pessoal.",
        )

    print("FASE 3 STAGING: Personal Knowledge Graph validado com sucesso.")


def main() -> int:
    try:
        run_validation()
        return 0
    except Exception as exc:
        print(f"FASE 3 STAGING: FALHA - {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
