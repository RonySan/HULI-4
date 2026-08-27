"""Modelos estáveis da personalidade conversacional da Huli."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ConversationMode(StrEnum):
    CASUAL = "casual"
    PROFESSIONAL = "professional"
    PRIVATE = "private"
    SERIOUS = "serious"
    RISK = "risk"


@dataclass(frozen=True, slots=True)
class PersonalityProfile:
    display_name: str = "Huli"
    technical_name: str = "HULI"
    acronym_meaning: str = "Humano Único Leal Inteligente"
    concise: bool = True
    casual_humor: bool = True
    professional_humor: bool = False
    private_humor: bool = False
    serious_humor: bool = False
    risk_humor: bool = False


@dataclass(frozen=True, slots=True)
class ConversationDecision:
    intent: str
    mode: ConversationMode
    reason: str
    is_followup: bool = False


DEFAULT_PROFILE = PersonalityProfile()

__all__ = [
    "ConversationDecision",
    "ConversationMode",
    "DEFAULT_PROFILE",
    "PersonalityProfile",
]
