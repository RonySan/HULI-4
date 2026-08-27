"""Capacidades especializadas acionadas pelo núcleo da Huli."""

from huli.skills.agenda_skill import AgendaSkill
from huli.skills.base import Skill
from huli.skills.conversation import ConversationSkill
from huli.skills.daily_summary_skill import DailySummarySkill
from huli.skills.foundation import FoundationSkill
from huli.skills.knowledge_skill import KnowledgeSkill
from huli.skills.memory_skill import MemorySkill
from huli.skills.planner_skill import PlannerSkill
from huli.skills.project_context import ProjectContextSkill
from huli.skills.registry import DuplicateSkillError, SkillRegistry
from huli.skills.smalltalk import SmallTalkSkill
from huli.skills.time_skill import TimeSkill

__all__ = [
    "AgendaSkill",
    "ConversationSkill",
    "DailySummarySkill",
    "DuplicateSkillError",
    "FoundationSkill",
    "KnowledgeSkill",
    "MemorySkill",
    "PlannerSkill",
    "ProjectContextSkill",
    "Skill",
    "SkillRegistry",
    "SmallTalkSkill",
    "TimeSkill",
]
