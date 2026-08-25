"""Composição das dependências da Huli.

Este módulo é o único ponto que conhece implementações concretas da fundação e
as conecta. O Kernel continua dependente apenas de contratos.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging

from huli.brain import IntentEngine
from huli.core import EventBus, Kernel
from huli.infrastructure import (
    EventRepository,
    InteractionRepository,
    RuntimeRecorder,
    Settings,
    SQLiteDatabase,
    configure_logging,
    load_settings,
)
from huli.security import AuthService, SecurityPolicy
from huli.skills import FoundationSkill, SkillRegistry


@dataclass(frozen=True, slots=True)
class HuliRuntime:
    """Dependências principais construídas para uma execução da Huli."""

    settings: Settings
    events: EventBus
    skills: SkillRegistry
    intents: IntentEngine
    kernel: Kernel
    logger: logging.Logger
    database: SQLiteDatabase
    interactions: InteractionRepository
    auth: AuthService
    security: SecurityPolicy


def build_runtime(settings: Settings | None = None) -> HuliRuntime:
    """Constrói a fundação da Huli sem usar estado global oculto."""
    resolved_settings = settings or load_settings()
    logger = configure_logging(resolved_settings)

    database = SQLiteDatabase(resolved_settings.database_path)
    database.initialize()

    events = EventBus()
    event_repository = EventRepository(database)
    interactions = InteractionRepository(database)
    RuntimeRecorder(events, event_repository, interactions)

    skills = SkillRegistry()
    skills.register(FoundationSkill())
    intents = IntentEngine()

    security = SecurityPolicy(
        max_input_chars=resolved_settings.max_input_chars,
        session_hours=resolved_settings.session_hours,
    )
    auth = AuthService(database, security)
    kernel = Kernel(handler=skills, event_bus=events)

    logger.info(
        "runtime_initialized environment=%s skills=%s schema=%s",
        resolved_settings.environment,
        ",".join(skills.names),
        database.schema_version(),
    )

    return HuliRuntime(
        settings=resolved_settings,
        events=events,
        skills=skills,
        intents=intents,
        kernel=kernel,
        logger=logger,
        database=database,
        interactions=interactions,
        auth=auth,
        security=security,
    )
