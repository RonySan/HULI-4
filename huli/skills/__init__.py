"""Capacidades especializadas acionadas pelo núcleo da Huli."""

from huli.skills.base import Skill
from huli.skills.foundation import FoundationSkill
from huli.skills.registry import DuplicateSkillError, SkillRegistry

__all__ = [
    "DuplicateSkillError",
    "FoundationSkill",
    "Skill",
    "SkillRegistry",
]
