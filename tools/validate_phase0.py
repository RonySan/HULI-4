"""Validação de regressão da fundação da Huli 4."""

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
    with TemporaryDirectory(prefix="huli-foundation-") as temp_dir:
        runtime = build_runtime(
            Settings(
                environment="validation",
                log_level="CRITICAL",
                data_dir=Path(temp_dir) / "data",
                session_hours=1,
            )
        )
        require(runtime.database.schema_version() >= 2, "Schema abaixo da fundação.")
        require("foundation" in runtime.skills.names, "FoundationSkill ausente.")

        owner = runtime.auth.create_owner("validation-owner")
        user, token = runtime.auth.authenticate("validation-owner")
        require(
            user.id == owner.id and bool(token),
            "Autenticação da fundação falhou.",
        )

        response = runtime.kernel.process(
            "ping",
            metadata={"session_id": "phase0-regression"},
        )
        require(
            response.handled_by == "foundation",
            "Ping não chegou à FoundationSkill.",
        )

        client = TestClient(create_app(runtime))
        require(
            client.get("/health").json()["version"] == __version__,
            "Health retornou versão incorreta.",
        )

    print("FUNDAÇÃO: regressão concluída com sucesso.")


def main() -> int:
    try:
        run_validation()
        return 0
    except Exception as exc:
        print(f"FUNDAÇÃO: FALHA - {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
