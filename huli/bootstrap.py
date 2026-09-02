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
    OpenMeteoWeatherService,
    PlannerService,
)
from huli.core import EventBus, Kernel
from huli.infrastructure import (
    ApplicationLauncher,
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
from huli.journal import (
    JournalBackupService,
    JournalPolicy,
    JournalRepository,
    JournalService,
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
from huli.security import AuthService, JournalVault, SecurityPolicy
from huli.security.privacy import filter_private_input
from huli.skills import (
    AgendaSkill,
    ApplicationSkill,
    ConversationSkill,
    DailySummarySkill,
    FoundationSkill,
    JournalSkill,
    KnowledgeSkill,
    MemorySkill,
    MorningBriefingSkill,
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
    weather: OpenMeteoWeatherService
    daily_summary: DailySummaryService
    memory: MemoryEngine
    memory_repository: MemoryRepository
    knowledge: KnowledgeService
    knowledge_repository: KnowledgeRepository
    journal: JournalService
    journal_repository: JournalRepository
    journal_vault: JournalVault
    journal_backups: JournalBackupService
    dispatcher: BrainDispatcher
    kernel: Kernel
    logger: logging.Logger
    database: SQLiteDatabase
    interactions: InteractionRepository
    tasks: TaskRepository
    appointments: AppointmentRepository
    applications: ApplicationLauncher
    auth: AuthService
    security: SecurityPolicy


def build_runtime(settings: Settings | None = None) -> HuliRuntime:
    resolved_settings = settings or load_settings()
    logger = configure_logging(resolved_settings)

    database = SQLiteDatabase(resolved_settings.database_path)
    database.initialize()

    security = SecurityPolicy(
        max_input_chars=resolved_settings.max_input_chars,
        session_hours=resolved_settings.session_hours,
    )
    auth = AuthService(database, security)
    journal_vault = JournalVault(
        database,
        inactivity_minutes=resolved_settings.journal_lock_minutes,
    )
    auth.bind_journal_vault(journal_vault)

    events = EventBus()
    event_repository = EventRepository(database)
    interactions = InteractionRepository(database)
    RuntimeRecorder(events, event_repository, interactions)

    tasks = TaskRepository(database)
    appointments = AppointmentRepository(database)
    applications = ApplicationLauncher()
    planner = PlannerService(tasks, events)
    agenda = AgendaService(appointments, events, resolved_settings.timezone)
    weather = OpenMeteoWeatherService(
        location=resolved_settings.weather_location,
        latitude=resolved_settings.weather_latitude,
        longitude=resolved_settings.weather_longitude,
        timezone_name=resolved_settings.timezone,
    )
    daily_summary = DailySummaryService(planner, agenda)

    memory_repository = MemoryRepository(database)
    memory = MemoryEngine(memory_repository, MemoryPolicy(), events)
    MemoryCandidateObserver(events, memory)

    knowledge_repository = KnowledgeRepository(database)
    knowledge = KnowledgeService(knowledge_repository, events)
    MemoryKnowledgeSynchronizer(events, memory_repository, knowledge)

    journal_repository = JournalRepository(database, journal_vault)
    journal = JournalService(
        journal_repository,
        JournalPolicy(),
        events,
        resolved_settings.timezone,
    )
    journal_backups = JournalBackupService(
        journal_repository,
        JournalPolicy(),
        resolved_settings.backup_dir,
    )

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
    skills.register(ApplicationSkill(applications))
    skills.register(DailySummarySkill(daily_summary))
    skills.register(MorningBriefingSkill(agenda, weather))
    skills.register(SmallTalkSkill(resolved_settings.timezone, personality=personality))
    skills.register(ConversationSkill(context))
    skills.register(JournalSkill(journal, resolved_settings.timezone, auth))
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
    kernel = Kernel(handler=dispatcher, event_bus=events, input_filter=filter_private_input)

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
        weather=weather,
        daily_summary=daily_summary,
        memory=memory,
        memory_repository=memory_repository,
        knowledge=knowledge,
        knowledge_repository=knowledge_repository,
        journal=journal,
        journal_repository=journal_repository,
        journal_vault=journal_vault,
        journal_backups=journal_backups,
        dispatcher=dispatcher,
        kernel=kernel,
        logger=logger,
        database=database,
        interactions=interactions,
        tasks=tasks,
        appointments=appointments,
        applications=applications,
        auth=auth,
        security=security,
    )
