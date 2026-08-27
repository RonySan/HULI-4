"""Validação ponta a ponta da evolução 4.1: diário pessoal privado."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from huli import __version__
from huli.api import create_app
from huli.bootstrap import build_runtime
from huli.infrastructure import Settings
from huli.personality import ConversationMode
from huli.security import PRIVATE_JOURNAL_REDACTION


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def run_validation() -> None:
    print(f"Validando diário pessoal privado em {__version__}...")

    with TemporaryDirectory(prefix="huli-journal-") as temp_dir:
        settings = Settings(
            environment="validation",
            log_level="CRITICAL",
            data_dir=Path(temp_dir) / "data",
            timezone="America/Sao_Paulo",
        )
        runtime = build_runtime(settings)
        runtime.auth.create_owner("rony", "1234")
        meta = {"session_id": "journal", "username": "rony", "role": "owner"}

        require(runtime.database.schema_version() >= 7, "Schema do diário não está ativo.")
        require("journal" in runtime.skills.names, "JournalSkill não foi registrada.")
        require(
            runtime.personality.decide(
                text="meu diário de hoje",
                intent="journal.list",
            ).mode
            is ConversationMode.PRIVATE,
            "Modo privado do diário falhou.",
        )

        private_sentence = "hoje finalizei uma evolução muito importante da Huli"
        saved = runtime.kernel.process(
            f"diário: {private_sentence} | humor: feliz | tags: trabalho, Huli",
            metadata=meta,
        )
        require(saved.handled_by == "journal" and saved.ok, "Registro natural falhou.")
        require(
            runtime.journal_repository.count_active("rony") == 1,
            "Entrada não foi persistida.",
        )
        require(
            runtime.memory_repository.count_active("rony") == 0,
            "Diário vazou para a memória automática.",
        )
        require(
            runtime.knowledge_repository.list_entities("rony") == (),
            "Diário vazou para o Knowledge Graph.",
        )

        listed = runtime.kernel.process("meu diário de hoje", metadata=meta)
        searched = runtime.kernel.process(
            "procure no meu diário por evolução",
            metadata=meta,
        )
        require(private_sentence in listed.text, "Consulta por data falhou.")
        require(private_sentence in searched.text, "Busca textual falhou.")

        edited = runtime.kernel.process(
            "edite a entrada #1 do diário: hoje finalizei e testei a evolução",
            metadata=meta,
        )
        require(edited.ok, "Edição explícita falhou.")
        require(
            "finalizei e testei" in runtime.journal_repository.get(1, "rony").content,
            "Edição não foi persistida.",
        )

        guest = runtime.kernel.process(
            "meu diário",
            metadata={"session_id": "guest", "username": "Visitante", "role": "guest"},
        )
        require(not guest.ok, "Visitante conseguiu acessar o diário.")

        secret = runtime.kernel.process(
            "diário: minha senha é segredo123",
            metadata=meta,
        )
        require(not secret.ok, "O diário aceitou uma senha.")
        require(
            runtime.journal_repository.count_active("rony") == 1,
            "Entrada secreta alterou o diário.",
        )

        latest = runtime.interactions.latest(1)[0]
        require(
            latest.user_text == PRIVATE_JOURNAL_REDACTION,
            "Solicitação privada apareceu nas interações técnicas.",
        )
        with runtime.database.connect() as connection:
            event_payloads = [
                json.loads(str(row["payload_json"]))
                for row in connection.execute("SELECT payload_json FROM events").fetchall()
            ]
        serialized_events = json.dumps(event_payloads, ensure_ascii=False)
        require(private_sentence not in serialized_events, "Conteúdo privado apareceu nos eventos.")
        require(
            runtime.context.recent_turns("journal")[0].text == PRIVATE_JOURNAL_REDACTION,
            "Conteúdo privado apareceu no contexto curto.",
        )

        restarted = build_runtime(settings)
        require(
            restarted.journal_repository.count_active("rony") == 1,
            "Diário não sobreviveu ao reinício.",
        )

        restarted.auth.create_owner("api-owner", "1234")
        client = TestClient(create_app(restarted))
        login = client.post(
            "/v1/auth/login",
            json={"username": "api-owner", "password": "1234"},
        )
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        api_saved = client.post(
            "/v1/messages",
            headers=headers,
            json={"text": "diário: entrada criada pela API", "session_id": "journal-api"},
        )
        require(
            api_saved.status_code == 200 and api_saved.json()["handled_by"] == "journal",
            "API não usou o diário do runtime comum.",
        )

        deleted = restarted.kernel.process(
            "apague a entrada #1 do diário",
            metadata=meta,
        )
        require(deleted.ok, "Exclusão lógica explícita falhou.")
        trash = restarted.kernel.process("lixeira do meu diário", metadata=meta)
        require("finalizei e testei" in trash.text, "Lixeira privada falhou.")
        restored = restarted.kernel.process(
            "restaure a entrada #1 do diário",
            metadata=meta,
        )
        require(restored.ok, "Restauração da entrada falhou.")

    print("FASE 4.1: diário pessoal privado validado com sucesso.")


def main() -> int:
    try:
        run_validation()
        return 0
    except Exception as exc:
        print(f"FASE 4.1: FALHA - {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
