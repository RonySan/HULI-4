"""Testes do Personal Knowledge Graph da Huli."""

from pathlib import Path

import pytest

from huli.bootstrap import build_runtime
from huli.infrastructure import Settings
from huli.knowledge import EntityKind


def build_test_runtime(tmp_path: Path):
    return build_runtime(
        Settings(environment="test", log_level="CRITICAL", data_dir=tmp_path)
    )


def test_entities_aliases_relations_and_facts_round_trip(tmp_path: Path) -> None:
    runtime = build_test_runtime(tmp_path)
    company = runtime.knowledge.ensure_entity(
        owner="rony",
        name="Impulso Digital",
        kind=EntityKind.COMPANY,
        aliases=("Impulso",),
    )
    project = runtime.knowledge.ensure_entity(
        owner="rony",
        name="Medynx",
        kind=EntityKind.PROJECT,
    )
    runtime.knowledge.add_relation(
        owner="rony",
        subject=project,
        predicate="desenvolvido_por",
        object_=company,
    )
    runtime.knowledge.add_fact(
        owner="rony",
        entity=project,
        key="status",
        value="em desenvolvimento",
    )

    resolved_alias = runtime.knowledge.resolve(owner="rony", query="Impulso")
    assert resolved_alias.id == company.id

    snapshot = runtime.knowledge.describe(owner="rony", query="Medynx")
    assert snapshot.entity.kind is EntityKind.PROJECT
    assert snapshot.outgoing[0][1].name == "Impulso Digital"
    assert snapshot.facts[0].value == "em desenvolvimento"


def test_memory_is_synchronized_into_relation_graph(tmp_path: Path) -> None:
    runtime = build_test_runtime(tmp_path)
    memory = runtime.memory.remember(
        owner="rony",
        content="Medynx depende de MySQL",
    )

    targets = runtime.knowledge.related(
        owner="rony",
        subject_query="Medynx",
        predicate="depende_de",
    )
    assert [item.name for item in targets] == ["MySQL"]

    relation = runtime.knowledge_repository.relations(
        owner="rony",
        entity_id=runtime.knowledge.resolve(owner="rony", query="Medynx").id,
        predicate="depende_de",
    )[0]
    assert relation.source_memory_id == memory.id


def test_forgetting_memory_deactivates_derived_knowledge(tmp_path: Path) -> None:
    runtime = build_test_runtime(tmp_path)
    memory = runtime.memory.remember(
        owner="rony",
        content="Medynx depende de MySQL",
    )
    runtime.memory.forget(owner="rony", target=str(memory.id))

    with pytest.raises(LookupError):
        runtime.knowledge.related(
            owner="rony",
            subject_query="Medynx",
            predicate="depende_de",
        )


def test_knowledge_is_isolated_by_owner(tmp_path: Path) -> None:
    runtime = build_test_runtime(tmp_path)
    runtime.memory.remember(owner="rony", content="Medynx depende de MySQL")
    runtime.memory.remember(owner="outro", content="Medynx depende de PostgreSQL")

    rony = runtime.knowledge.related(
        owner="rony",
        subject_query="Medynx",
        predicate="depende_de",
    )
    outro = runtime.knowledge.related(
        owner="outro",
        subject_query="Medynx",
        predicate="depende_de",
    )

    assert [item.name for item in rony] == ["MySQL"]
    assert [item.name for item in outro] == ["PostgreSQL"]
