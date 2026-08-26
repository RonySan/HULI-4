"""Classificação determinística de intenções fundamentais da Huli."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import re
from typing import Mapping

from huli.brain.normalization import normalize_text


class IntentName(StrEnum):
    """Intenções locais reconhecidas no início da Fase 1."""

    SYSTEM_STATUS = "system.status"
    TIME_QUERY = "time.query"
    AGENDA_QUERY = "agenda.query"
    TASK_CREATE = "task.create"
    SMALL_TALK = "smalltalk"
    PROJECT_QUERY = "project.query"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class IntentMatch:
    """Resultado estruturado produzido pelo Intent Engine."""

    intent: IntentName
    confidence: float
    normalized_text: str
    metadata: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class _IntentRule:
    intent: IntentName
    pattern: re.Pattern[str]
    confidence: float
    name: str


class IntentEngine:
    """Classifica intenções sem executar qualquer ação."""

    def __init__(self) -> None:
        self._rules = (
            _IntentRule(
                IntentName.PROJECT_QUERY,
                re.compile(r"\b(?:status|situacao|andamento|como esta)\b.*\bprojeto\b|\bprojeto\b.*\b(?:status|situacao|andamento)\b"),
                0.98,
                "project-status",
            ),
            _IntentRule(
                IntentName.TASK_CREATE,
                re.compile(
                    r"^(?:adiciona|adicionar|adicione|cria|criar|crie|anota|anotar|anote|registre|registrar)\b.*\b(?:tarefa|lembrete)\b"
                    r"|^(?:nova|criar uma|adicionar uma)\s+tarefa\b"
                ),
                0.97,
                "task-create",
            ),
            _IntentRule(
                IntentName.AGENDA_QUERY,
                re.compile(
                    r"\b(?:minha agenda|agenda de hoje|agenda hoje|compromissos hoje|meus compromissos)\b"
                    r"|\bo que (?:eu )?(?:tenho|temos) (?:para|pra) fazer hoje\b"
                    r"|\bo que (?:eu )?tenho hoje\b"
                ),
                0.96,
                "agenda-query",
            ),
            _IntentRule(
                IntentName.SYSTEM_STATUS,
                re.compile(
                    r"^(?:qual (?:e )?o )?status (?:da )?huli$"
                    r"|^status huli$"
                    r"|^huli (?:esta|ta) (?:ativa|funcionando|online)$"
                ),
                0.99,
                "huli-status",
            ),
            _IntentRule(
                IntentName.TIME_QUERY,
                re.compile(
                    r"^(?:que horas (?:sao|e)|qual (?:e )?a hora|qual (?:e )?o horario|horario agora|hora agora)(?: por favor)?$"
                ),
                0.99,
                "time-query",
            ),
            _IntentRule(
                IntentName.SMALL_TALK,
                re.compile(
                    r"^(?:(?:oi|ola|opa|e ai)(?: huli)?(?: (?:bom dia|boa tarde|boa noite))?"
                    r"|(?:bom dia|boa tarde|boa noite)(?: huli)?"
                    r"|(?:tudo bem|como voce esta|como vai)(?: huli)?"
                    r"|huli (?:tudo bem|como voce esta|como vai))$"
                    r"|^(?:obrigado|obrigada|valeu|agradecido|agradecida)(?: huli)?$"
                    r"|^(?:tchau|ate logo|ate mais)(?: huli)?$"
                ),
                0.95,
                "small-talk",
            ),
        )

    def classify(self, text: str) -> IntentMatch:
        """Classifica o texto usando somente regras locais e determinísticas."""
        normalized = normalize_text(text)
        if not normalized:
            return IntentMatch(
                intent=IntentName.UNKNOWN,
                confidence=0.0,
                normalized_text=normalized,
                metadata={"matched_rule": "empty"},
            )

        for rule in self._rules:
            if rule.pattern.search(normalized):
                return IntentMatch(
                    intent=rule.intent,
                    confidence=rule.confidence,
                    normalized_text=normalized,
                    metadata={"matched_rule": rule.name},
                )

        return IntentMatch(
            intent=IntentName.UNKNOWN,
            confidence=0.0,
            normalized_text=normalized,
            metadata={"matched_rule": "none"},
        )
