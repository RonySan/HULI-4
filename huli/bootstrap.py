"""Composição das dependências da Huli.

Este módulo é o único ponto que conhece implementações concretas da fundação e
as conecta. O Kernel continua dependente apenas de contratos.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging

from huli.core import EventBus, Kernel
from huli.infrastructure.config import Settings, load_settings
from huli.infrastructure.logging import configure_logging
from huli.skills import FoundationSkill, SkillRegistry


@dataclass(frozen=True, slots=True)
class HuliRuntime:
    """Dependências principais construídas para uma execução da Huli."""

    settings: Settings
    events: EventBus
    skills: SkillRegistry
    kernel: Kernel
    logger: logging.Logger


def build_runtime(settings: Settings | None = None) -> HuliRuntime:
    """Constrói a fundação da Huli sem usar estado global oculto."""
    resolved_settings = settings or load_settings()
    logger = configure_logging(resolved_settings)
    events = EventBus()
    skills = SkillRegistry()
    skills.register(FoundationSkill())
    kernel = Kernel(handler=skills, event_bus=events)

    logger.info(
        "runtime_initialized environment=%s skills=%s",
        resolved_settings.environment,
        ",".join(skills.names),
    )

    return HuliRuntime(
        settings=resolved_settings,
        events=events,
        skills=skills,
        kernel=kernel,
        logger=logger,
    )
