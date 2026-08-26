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
