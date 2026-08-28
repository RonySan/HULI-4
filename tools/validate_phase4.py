"""Validação ponta a ponta da Fase 4: personalidade e conversação."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from huli import __version__
from huli.api import create_app
from huli.bootstrap import build_runtime
from huli.core import Event
from huli.infrastructure import Settings


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def run_validation() -> None:
    print(f"Validando Fase 4 em {__version__}...")

    with TemporaryDirectory(prefix="huli-phase4-") as temp_dir:
        runtime = build_runtime(
            Settings(
                environment="validation",
                log_level="CRITICAL",
                data_dir=Path(temp_dir) / "data",
                timezone="America/Sao_Paulo",
            )
        )
        meta = {
            "session_id": "phase4-owner",
            "username": "rony",
            "role": "owner",
        }
        conversation_events: list[Event] = []
        runtime.events.subscribe("brain.conversation.updated", conversation_events.append)

        require(__version__ == "4.0.0-alpha.9", "Versão da Fase 4 incorreta.")
        require(runtime.database.schema_version() >= 6, "Schema anterior regrediu.")
        require("conversation-mode" in runtime.skills.names, "ConversationModeSkill ausente.")

        mode = runtime.kernel.process("modo profissional", metadata=meta)
        require(mode.handled_by == "conversation-mode", "Modo profissional não foi ativado.")
        require(
            runtime.conversation.snapshot("phase4-owner").mode.value == "professional",
            "Modo profissional não persistiu na sessão.",
        )

        greeting = runtime.kernel.process("oi Huli", metadata=meta)
        require(greeting.handled_by == "smalltalk", "Small Talk falhou na Fase 4.")
        require(
            "objetiva" in greeting.text or "projetos" in greeting.text,
            "Small Talk não respeitou modo profissional.",
        )

        normal_identity = runtime.kernel.process("quem é você?", metadata=meta)
        meaning = runtime.kernel.process("o que significa Huli?", metadata=meta)
        require("Sou a Huli" in normal_identity.text, "Identidade básica falhou.")
        require(
            "Humano Único Leal Inteligente" not in normal_identity.text,
            "A sigla foi expandida sem ser solicitada.",
        )
        require(
            "Humano Único Leal Inteligente" in meaning.text,
            "A sigla não foi explicada quando solicitada.",
        )

        runtime.kernel.process("modo automático", metadata=meta)
        frustration = runtime.kernel.process(
            "não está funcionando, deu errado de novo",
            metadata=meta,
        )
        serious = runtime.conversation.snapshot("phase4-owner")
        require(frustration.ok is False, "Fallback de frustração deveria ser controlado.")
        require(serious.mode.value == "serious", "Frustração não ativou modo sério.")
        require(not serious.humor_allowed, "Humor ficou ativo em modo sério.")
        require("não vou fingir" in frustration.text, "Fallback de frustração ficou genérico.")

        runtime.kernel.process("modo casual", metadata=meta)
        risk_response = runtime.kernel.process("apagar tudo agora", metadata=meta)
        risk = runtime.conversation.snapshot("phase4-owner")
        require(risk.mode.value == "risk", "Risco não prevaleceu sobre modo casual.")
        require(not risk.humor_allowed, "Humor ficou ativo em risco.")
        require("sensível" in risk_response.text, "Fallback de risco não foi aplicado.")

        runtime.kernel.process("oi Huli", metadata=meta)
        require(
            runtime.conversation.snapshot("phase4-owner").mode.value == "casual",
            "Modo casual manual não retornou após solicitação de risco.",
        )

        runtime.kernel.process(
            "lembre que eu prefiro relatórios objetivos",
            metadata=meta,
        )
        recall = runtime.kernel.process(
            "o que você lembra sobre relatórios?",
            metadata=meta,
        )
        require(
            "relatórios objetivos" in recall.text,
            "Personalidade alterou ou perdeu fato da Memory Engine.",
        )

        require(
            runtime.security.guest_can_execute("modo casual", "conversation.mode.set"),
            "Visitante não pode controlar o estilo da própria sessão.",
        )
        require(
            not runtime.security.guest_can_execute("minhas memórias", "memory.list"),
            "Visitante recebeu acesso indevido à memória.",
        )

        runtime.auth.create_owner("api-owner", "1234")
        client = TestClient(create_app(runtime))
        login = client.post(
            "/v1/auth/login",
            json={"username": "api-owner", "password": "1234"},
        )
        require(login.status_code == 200, "Login da API falhou.")
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        api_mode = client.post(
            "/v1/messages",
            headers=headers,
            json={"text": "modo profissional", "session_id": "phase4-api"},
        )
        api_greeting = client.post(
            "/v1/messages",
            headers=headers,
            json={"text": "oi Huli", "session_id": "phase4-api"},
        )
        require(
            api_mode.status_code == 200
            and api_mode.json()["conversation_mode"] == "professional",
            "API não ativou modo profissional.",
        )
        require(
            api_greeting.json()["conversation_mode"] == "professional",
            "API perdeu estado conversacional por session_id.",
        )
        require(
            "conversation_signal" in api_greeting.json()
            and "humor_allowed" in api_greeting.json(),
            "API não expôs metadados da Fase 4.",
        )

        require(len(conversation_events) >= 10, "Eventos de conversação não foram publicados.")

    print("FASE 4: personalidade e conversação validadas com sucesso.")


def main() -> int:
    try:
        run_validation()
        return 0
    except Exception as exc:
        print(f"FASE 4: FALHA - {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
