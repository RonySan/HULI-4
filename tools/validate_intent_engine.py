"""Validação do Intent Engine e do roteamento consciente da Fase 1."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from huli.brain import IntentEngine, IntentName
from huli.bootstrap import build_runtime
from huli.infrastructure import Settings


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def run_validation() -> None:
    engine = IntentEngine()
    cases = (("que horas são?", IntentName.TIME_QUERY), ("agenda dentista amanhã às 15:00", IntentName.AGENDA_CREATE), ("tarefas pendentes", IntentName.TASK_LIST), ("oi huli, bom dia", IntentName.SMALL_TALK), ("vamos falar do projeto Medynx", IntentName.PROJECT_SET), ("trocar o trocador de calor da piscina", IntentName.UNKNOWN))
    for text, expected in cases:
        result = engine.classify(text)
        print(f"  {text!r} -> {result.intent.value} ({result.confidence:.2f})")
        require(result.intent is expected, f"Intenção incorreta para {text!r}.")
    with TemporaryDirectory(prefix="huli-intent-") as temp_dir:
        runtime = build_runtime(Settings(environment="validation", log_level="CRITICAL", data_dir=Path(temp_dir) / "data"))
        meta = {"session_id": "intent-validation", "username": "rony", "role": "owner"}
        require(runtime.kernel.process("que horas são?", metadata=meta).handled_by == "time", "TimeSkill não recebeu time.query.")
        require(runtime.kernel.process("oi huli, bom dia", metadata=meta).handled_by == "smalltalk", "SmallTalkSkill não recebeu smalltalk.")
    print("INTENT + DISPATCHER: validação concluída com sucesso.")


def main() -> int:
    try:
        run_validation(); return 0
    except Exception as exc:
        print(f"INTENT + DISPATCHER: FALHA - {exc}"); return 1


if __name__ == "__main__":
    raise SystemExit(main())
