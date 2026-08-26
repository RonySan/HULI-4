from pathlib import Path

from huli.bootstrap import build_runtime
from huli.infrastructure import Settings


def test_phase1_brain_end_to_end(tmp_path: Path) -> None:
    runtime = build_runtime(Settings(environment="test", log_level="CRITICAL", data_dir=tmp_path, timezone="America/Sao_Paulo"))
    meta = {"session_id": "s1", "username": "rony", "role": "owner"}
    assert runtime.kernel.process("oi huli, bom dia", metadata=meta).handled_by == "smalltalk"
    assert runtime.kernel.process("que horas são?", metadata=meta).handled_by == "time"
    project = runtime.kernel.process("vamos falar do projeto Medynx", metadata=meta)
    assert project.handled_by == "project-context"
    task = runtime.kernel.process("adiciona uma tarefa revisar o banco prioridade alta", metadata=meta)
    assert task.handled_by == "planner"
    stored = runtime.tasks.list_pending(project="Medynx")
    assert len(stored) == 1 and stored[0].priority == "alta"
    listing = runtime.kernel.process("tarefas pendentes", metadata=meta)
    assert "revisar o banco" in listing.text
    appointment = runtime.kernel.process("agenda dentista amanhã às 15:00", metadata=meta)
    assert appointment.handled_by == "agenda"
    assert len(runtime.agenda.upcoming(limit=10)) == 1
    summary = runtime.kernel.process("resumo do dia", metadata=meta)
    assert summary.handled_by == "daily-summary"
    completed = runtime.kernel.process(f"concluir tarefa {stored[0].id}", metadata=meta)
    assert "concluída" in completed.text
    unknown = runtime.kernel.process("abrir o chrome", metadata=meta)
    assert unknown.handled_by == "brain-dispatcher" and unknown.ok is False
