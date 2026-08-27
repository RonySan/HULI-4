"""Validação ponta a ponta da Fase 4 staging: personalidade e conversação."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from huli import __version__
from huli.api import create_app
from huli.bootstrap import build_runtime
from huli.infrastructure import Settings
from huli.personality import ConversationMode


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def run_validation() -> None:
    print(f"Validando Fase 4 staging em {__version__}...")

    with TemporaryDirectory(prefix="huli-phase4-") as temp_dir:
        runtime = build_runtime(
            Settings(
                environment="validation",
                log_level="CRITICAL",
                data_dir=Path(temp_dir) / "data",
                timezone="America/Sao_Paulo",
            )
        )
        meta = {"session_id": "phase4", "username": "rony", "role": "owner"}

        require(runtime.database.schema_version() >= 6, "Schema mínimo da staging não está ativo.")
        require(
            "conversation" in runtime.skills.names,
            "ConversationSkill não foi registrada.",
        )
        require(
            runtime.personality.decide(text="oi huli", intent="smalltalk").mode
            is ConversationMode.CASUAL,
            "Modo casual falhou.",
        )
        require(
            runtime.personality.decide(text="minhas tarefas", intent="task.list").mode
            is ConversationMode.PROFESSIONAL,
            "Modo profissional falhou.",
        )
        require(
            runtime.personality.decide(
                text="falha crítica urgente",
                intent="unknown",
            ).mode
            is ConversationMode.SERIOUS,
            "Modo sério falhou.",
        )
        require(
            runtime.personality.decide(text="esqueça 1", intent="memory.forget").mode
            is ConversationMode.RISK,
            "Modo de risco falhou.",
        )

        greeting = runtime.kernel.process("oi huli", metadata=meta)
        followup = runtime.kernel.process("e você?", metadata=meta)
        require(greeting.handled_by == "smalltalk", "Saudação não chegou ao Small Talk.")
        require(followup.handled_by == "smalltalk", "Continuidade social curta falhou.")

        work_start = runtime.kernel.process(
            "ok, então vamos começar os trabalhos de hoje",
            metadata=meta,
        )
        require(
            work_start.handled_by == "smalltalk"
            and "primeira prioridade" in work_start.text.casefold(),
            "Início natural do trabalho não foi reconhecido.",
        )

        date = runtime.kernel.process("que dia é hoje?", metadata=meta)
        require(
            date.handled_by == "time" and date.text.startswith("Hoje é "),
            "Consulta natural da data falhou.",
        )

        for agenda_query in (
            "como está a agenda pra hoje?",
            "como está nossa agenda essa noite?",
            "agenda",
        ):
            agenda_response = runtime.kernel.process(agenda_query, metadata=meta)
            require(
                agenda_response.handled_by == "agenda",
                f"Consulta natural de agenda falhou: {agenda_query}",
            )

        natural_appointment = runtime.kernel.process(
            "agenda pra mim jantar às 22 horas com a Gisele",
            metadata=meta,
        )
        require(
            natural_appointment.handled_by == "agenda"
            and natural_appointment.ok
            and runtime.agenda.upcoming(limit=10),
            "Criação natural de compromisso sem data explícita falhou.",
        )

        identity = runtime.kernel.process("o que significa Huli?", metadata=meta)
        require(
            "Humano Único Leal Inteligente" in identity.text,
            "Identidade técnica não foi explicada quando solicitada.",
        )

        runtime.kernel.process("vamos falar do projeto Medynx", metadata=meta)
        work_tone = runtime.kernel.process("como você está huli?", metadata=meta)
        require(
            "seguir com o trabalho" in work_tone.text.casefold(),
            "Contexto de trabalho não selecionou resposta profissional.",
        )

        project_update = runtime.kernel.process(
            "o Medynx é um novo projeto desenvolvido para clínicas, "
            "depois precisamos rever os logins dos pacientes",
            metadata=meta,
        )
        require(
            project_update.handled_by == "project-context" and project_update.ok,
            "Informação natural do projeto não foi registrada.",
        )
        require(
            runtime.tasks.list_pending(project="Medynx"),
            "Tarefa embutida na atualização do projeto não foi criada.",
        )
        project_knowledge = runtime.kernel.process(
            "o que você sabe sobre Medynx?",
            metadata=meta,
        )
        require(
            "descrição:" in project_knowledge.text,
            "Atualização natural não chegou ao Knowledge Graph.",
        )

        priority = runtime.kernel.process(
            "adiciona uma tarefa revisar o banco prioridade alto",
            metadata=meta,
        )
        require(
            "prioridade alta" in priority.text
            and runtime.tasks.list_pending(project="Medynx")[0].priority == "alta",
            "Variação 'prioridade alto' não foi normalizada.",
        )

        recap = runtime.kernel.process("o que conversamos mais cedo?", metadata=meta)
        require(
            recap.handled_by == "conversation"
            and "Medynx" in recap.text,
            "Resumo factual da conversa atual falhou.",
        )

        runtime.kernel.process(
            "lembre que eu prefiro relatórios objetivos",
            metadata=meta,
        )
        recalled = runtime.kernel.process(
            "o que você lembra sobre relatórios?",
            metadata=meta,
        )
        require(
            recalled.handled_by == "memory" and recalled.text.startswith("Encontrei"),
            "Personalidade alterou indevidamente uma resposta factual da memória.",
        )

        runtime.auth.create_owner("api-owner", "1234")
        client = TestClient(create_app(runtime))
        login = client.post(
            "/v1/auth/login",
            json={"username": "api-owner", "password": "1234"},
        )
        require(login.status_code == 200, "Login HTTP falhou.")
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        api_first = client.post(
            "/v1/messages",
            headers=headers,
            json={"text": "oi huli", "session_id": "phase4-api"},
        )
        api_followup = client.post(
            "/v1/messages",
            headers=headers,
            json={"text": "e você?", "session_id": "phase4-api"},
        )
        require(
            api_first.status_code == 200 and api_first.json()["handled_by"] == "smalltalk",
            "API não usou a personalidade do runtime comum.",
        )
        require(
            api_followup.status_code == 200
            and api_followup.json()["handled_by"] == "smalltalk",
            "API perdeu continuidade social da sessão.",
        )

    print("FASE 4 STAGING: personalidade e conversação validadas com sucesso.")


def main() -> int:
    try:
        run_validation()
        return 0
    except Exception as exc:
        print(f"FASE 4 STAGING: FALHA - {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
