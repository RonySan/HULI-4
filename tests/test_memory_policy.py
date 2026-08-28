from pathlib import Path

import pytest

from huli.core import EventBus
from huli.infrastructure import SQLiteDatabase
from huli.memory import (
    MemoryEngine,
    MemoryKind,
    MemoryPolicy,
    MemoryPolicyError,
    MemoryRepository,
)


def build_engine(tmp_path: Path) -> MemoryEngine:
    database = SQLiteDatabase(tmp_path / "huli.db")
    database.initialize()
    return MemoryEngine(MemoryRepository(database), MemoryPolicy(), EventBus())


def test_secret_memory_is_rejected_even_when_explicit(tmp_path: Path) -> None:
    engine = build_engine(tmp_path)

    with pytest.raises(MemoryPolicyError, match="não armazena senhas"):
        engine.remember(
            owner="rony",
            content="minha senha é exemplo123",
            explicit=True,
        )


def test_sensitive_memory_requires_explicit_owner_action(tmp_path: Path) -> None:
    engine = build_engine(tmp_path)

    explicit = engine.remember(
        owner="rony",
        content="meu documento pessoal está arquivado no cofre",
        explicit=True,
    )
    assert explicit.sensitivity.value == "sensitive"

    with pytest.raises(MemoryPolicyError, match="sensível exige memória explícita"):
        engine.remember(
            owner="rony",
            content="meu documento pessoal está arquivado na gaveta",
            explicit=False,
            confidence=0.99,
        )


def test_low_confidence_automatic_learning_is_rejected(tmp_path: Path) -> None:
    engine = build_engine(tmp_path)

    with pytest.raises(MemoryPolicyError, match="confiança"):
        engine.remember(
            owner="rony",
            content="prefiro interface escura",
            kind=MemoryKind.PREFERENCE,
            explicit=False,
            confidence=0.50,
        )


def test_high_confidence_safe_candidate_can_be_learned(tmp_path: Path) -> None:
    engine = build_engine(tmp_path)

    memory = engine.remember(
        owner="rony",
        content="prefiro interface escura",
        kind=MemoryKind.PREFERENCE,
        explicit=False,
        confidence=0.95,
    )

    assert memory.kind is MemoryKind.PREFERENCE
    assert memory.source.value == "automatic"
