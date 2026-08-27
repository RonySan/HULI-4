"""Testes do domínio persistente do diário pessoal."""

from datetime import date
from pathlib import Path

import pytest

from huli.bootstrap import build_runtime
from huli.infrastructure import Settings
from huli.journal import JournalPolicyError


def build_test_runtime(tmp_path: Path):
    return build_runtime(
        Settings(
            environment="test",
            log_level="CRITICAL",
            data_dir=tmp_path,
            timezone="America/Sao_Paulo",
        )
    )


def test_journal_create_search_update_soft_delete_and_restore(tmp_path: Path) -> None:
    runtime = build_test_runtime(tmp_path)
    entry = runtime.journal.create(
        owner="rony",
        content="Consegui finalizar a primeira versão do diário da Huli.",
        entry_date=date(2026, 8, 27),
        mood="Feliz",
        tags=("Trabalho", "Huli", "trabalho"),
    )

    assert runtime.database.schema_version() == 7
    assert entry.owner == "rony"
    assert entry.entry_date == date(2026, 8, 27)
    assert entry.mood == "feliz"
    assert entry.tags == ("trabalho", "huli")
    assert entry.sensitivity.value == "normal"
    assert runtime.journal.search(owner="rony", query="primeira versão Huli") == (
        entry,
    )

    updated = runtime.journal.update(
        owner="rony",
        entry_id=entry.id,
        content="Finalizei e validei o diário privado da Huli.",
        preserve_mood=True,
        preserve_tags=True,
    )
    assert updated.content == "Finalizei e validei o diário privado da Huli."
    assert updated.mood == "feliz"
    assert updated.tags == ("trabalho", "huli")

    deleted = runtime.journal.delete(owner="rony", entry_id=entry.id)
    assert deleted.is_active is False
    assert deleted.deleted_at is not None
    assert runtime.journal_repository.count_active("rony") == 0
    assert runtime.journal.trash(owner="rony") == (deleted,)

    restored = runtime.journal.restore(owner="rony", entry_id=entry.id)
    assert restored.is_active is True
    assert restored.deleted_at is None
    assert runtime.journal_repository.count_active("rony") == 1


def test_journal_is_strictly_isolated_by_owner(tmp_path: Path) -> None:
    runtime = build_test_runtime(tmp_path)
    rony = runtime.journal.create(
        owner="rony",
        content="Entrada que pertence somente ao Rony.",
    )
    runtime.journal.create(
        owner="outro",
        content="Entrada pertencente a outro usuário.",
    )

    assert runtime.journal_repository.count_active("rony") == 1
    assert runtime.journal_repository.count_active("outro") == 1
    assert runtime.journal.search(owner="outro", query="Rony") == ()
    with pytest.raises(LookupError):
        runtime.journal.delete(owner="outro", entry_id=rony.id)


def test_journal_accepts_sensitive_life_notes_but_rejects_secrets(
    tmp_path: Path,
) -> None:
    runtime = build_test_runtime(tmp_path)

    health_note = runtime.journal.create(
        owner="rony",
        content="Hoje acompanhei uma consulta de saúde da família.",
    )
    assert health_note.sensitivity.value == "sensitive"

    with pytest.raises(JournalPolicyError, match="não armazena senhas"):
        runtime.journal.create(
            owner="rony",
            content="Minha senha é segredo123.",
        )
    assert runtime.journal_repository.count_active("rony") == 1


def test_journal_survives_runtime_restart(tmp_path: Path) -> None:
    settings = Settings(
        environment="test",
        log_level="CRITICAL",
        data_dir=tmp_path,
        timezone="America/Sao_Paulo",
    )
    first = build_runtime(settings)
    first.journal.create(
        owner="rony",
        content="Esta entrada precisa continuar disponível depois de reiniciar.",
    )

    second = build_runtime(settings)

    assert second.journal_repository.count_active("rony") == 1
    assert "continuar disponível" in second.journal.recent(owner="rony")[0].content
