"""Composição das dependências da Huli."""

from __future__ import annotations

from dataclasses import dataclass
import logging

from huli.brain import (
    AgendaService,
    BrainDispatcher,
    ContextEngine,
    DailySummaryService,
    IntentEngine,
    PlannerService,
)
from huli.core import EventBus, Kernel
from huli.infrastructure import (
    AppointmentRepository,
    EventRepository,
    InteractionRepository,
    RuntimeRecorder,
    Settings,
    SQLiteDatabase,
    TaskRepository,
    configure_logging,
    load_settings,
)
from huli.knowledge import (
    KnowledgeRepository,
    KnowledgeService,
    MemoryKnowledgeSynchronizer,
)
from huli.memory import (
    MemoryCandidateObserver,
    MemoryEngine,
    MemoryPolicy,
    MemoryRepository,
)
from huli.personality import PersonalityEngine
from huli.security import AuthService, SecurityPolicy
from huli.skills import (
    AgendaSkill,
    ConversationSkill,
    DailySummarySkill,
    FoundationSkill,
    KnowledgeSkill,
    MemorySkill,
    PlannerSkill,
    ProjectContextSkill,
    SkillRegistry,
    SmallTalkSkill,
    TimeSkill,
)


@dataclass(frozen=True, slots=True)
class HuliRuntime:
    settings: Settings
    events: EventBus
    skills: SkillRegistry
    intents: IntentEngine
    context: ContextEngine
    personality: PersonalityEngine
    planner: PlannerService
    agenda: AgendaService
    daily_summary: DailySummaryService
    memory: MemoryEngine
    memory_repository: MemoryRepository
    knowledge: KnowledgeService
    knowledge_repository: KnowledgeRepository
    dispatcher: BrainDispatcher
    kernel: Kernel
    logger: logging.Logger
    database: SQLiteDatabase
    interactions: InteractionRepository
    tasks: TaskRepository
    appointments: AppointmentRepository
    auth: AuthService
    security: SecurityPolicy


def build_runtime(settings: Settings | None = None) -> HuliRuntime:
    resolved_settings = settings or load_settings()
    logger = configure_logging(resolved_settings)

    database = SQLiteDatabase(resolved_settings.database_path)
    database.initialize()

    events = EventBus()
    event_repository = EventRepository(database)
    interactions = InteractionRepository(database)
    RuntimeRecorder(events, event_repository, interactions)

    tasks = TaskRepository(database)
    appointments = AppointmentRepository(database)
    planner = PlannerService(tasks, events)
    agenda = AgendaService(appointments, events, resolved_settings.timezone)
    daily_summary = DailySummaryService(planner, agenda)

    memory_repository = MemoryRepository(database)
    memory = MemoryEngine(memory_repository, MemoryPolicy(), events)
    MemoryCandidateObserver(events, memory)

    knowledge_repository = KnowledgeRepository(database)
    knowledge = KnowledgeService(knowledge_repository, events)
    MemoryKnowledgeSynchronizer(events, memory_repository, knowledge)

    intents = IntentEngine()
    context = ContextEngine(max_turns=resolved_settings.context_turns)
    personality = PersonalityEngine(
        events,
        timezone_name=resolved_settings.timezone,
    )

    skills = SkillRegistry()
    skills.register(FoundationSkill())
    skills.register(TimeSkill(resolved_settings.timezone))
    skills.register(PlannerSkill(planner))
    skills.register(AgendaSkill(agenda, resolved_settings.timezone))
    skills.register(DailySummarySkill(daily_summary))
    skills.register(SmallTalkSkill(resolved_settings.timezone, personality=personality))
    skills.register(ConversationSkill(context))
    skills.register(ProjectContextSkill(context, planner, memory))
    skills.register(MemorySkill(memory))
    skills.register(KnowledgeSkill(knowledge))

    dispatcher = BrainDispatcher(
        intents=intents,
        context=context,
        skills=skills,
        event_bus=events,
        personality=personality,
    )
    security = SecurityPolicy(
        max_input_chars=resolved_settings.max_input_chars,
        session_hours=resolved_settings.session_hours,
    )
    auth = AuthService(database, security)
    kernel = Kernel(handler=dispatcher, event_bus=events)

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
        context=context,
        personality=personality,
        planner=planner,
        agenda=agenda,
        daily_summary=daily_summary,
        memory=memory,
        memory_repository=memory_repository,
        knowledge=knowledge,
        knowledge_repository=knowledge_repository,
        dispatcher=dispatcher,
        kernel=kernel,
        logger=logger,
        database=database,
        interactions=interactions,
        tasks=tasks,
        appointments=appointments,
        auth=auth,
        security=security,
    )
