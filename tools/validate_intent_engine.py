"""Validação isolada do Intent Engine da Fase 1.1."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from huli.brain import IntentEngine, IntentName
from huli.bootstrap import build_runtime
from huli.core import Event
from huli.infrastructure import Settings


class ValidationFailure(RuntimeError):
    """Falha em um requisito obrigatório do Intent Engine."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationFailure(message)


def run_validation() -> None:
    engine = IntentEngine()
    cases = (
        ("que horas são?", IntentName.TIME_QUERY),
        ("qual o status da Huli?", IntentName.SYSTEM_STATUS),
        ("o que temos pra fazer hoje?", IntentName.AGENDA_QUERY),
        ("adiciona uma tarefa revisar o Medynx", IntentName.TASK_CREATE),
        ("oi Huli", IntentName.SMALL_TALK),
        ("qual o status do projeto Medynx?", IntentName.PROJECT_QUERY),
        ("trocar o trocador de calor da piscina", IntentName.UNKNOWN),
    )

    print("Validando classificações do Intent Engine...")
    for text, expected in cases:
        result = engine.classify(text)
        print(f"  {text!r} -> {result.intent.value} ({result.confidence:.2f})")
        require(
            result.intent is expected,
            f"Intenção incorreta para {text!r}: esperado {expected.value}, recebido {result.intent.value}.",
        )

    with TemporaryDirectory(prefix="huli-intent-") as temp_dir:
        runtime = build_runtime(
            Settings(
                environment="validation",
                log_level="CRITICAL",
                data_dir=Path(temp_dir) / "data",
            )
        )
        captured: list[Event] = []
        runtime.events.subscribe("brain.intent.classified", captured.append)

        runtime.kernel.process("status huli")
        require(len(captured) == 1, "O runtime não publicou exatamente um evento de intenção.")
        require(
            captured[0].payload.get("intent") == IntentName.SYSTEM_STATUS.value,
            "O evento brain.intent.classified contém intenção incorreta.",
        )

    print("INTENT ENGINE: validação concluída com sucesso.")


def main() -> int:
    try:
        run_validation()
    except Exception as exc:
        print(f"INTENT ENGINE: FALHA - {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
