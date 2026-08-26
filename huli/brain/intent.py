"""Classificação determinística de intenções fundamentais da Huli."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import re
from typing import Mapping

from huli.brain.normalization import normalize_text


class IntentName(StrEnum):
    SYSTEM_STATUS = "system.status"
    TIME_QUERY = "time.query"
    AGENDA_QUERY = "agenda.query"
    AGENDA_CREATE = "agenda.create"
    AGENDA_CANCEL = "agenda.cancel"
    TASK_CREATE = "task.create"
    TASK_LIST = "task.list"
    TASK_COMPLETE = "task.complete"
    DAILY_SUMMARY = "daily.summary"
    SMALL_TALK = "smalltalk"
    PROJECT_SET = "project.set"
    PROJECT_QUERY = "project.query"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class IntentMatch:
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
    def __init__(self) -> None:
        self._rules = (
            _IntentRule(IntentName.PROJECT_SET, re.compile(r"^(?:vamos falar (?:do|sobre o)|estamos no|mude para o|usar o) projeto\b|^projeto atual (?:e|eh)\b|^defina (?:o )?projeto\b"), 0.99, "project-set"),
            _IntentRule(IntentName.PROJECT_QUERY, re.compile(r"\b(?:qual projeto (?:estamos|esta ativo)|projeto ativo)\b|\b(?:status|situacao|andamento|como esta)\b.*\bprojeto\b|\bprojeto\b.*\b(?:status|situacao|andamento)\b"), 0.98, "project-query"),
            _IntentRule(IntentName.TASK_COMPLETE, re.compile(r"^(?:conclui|concluir|conclua|finaliza|finalizar|finalize|marque|marca)\b.*\btarefa\b|^(?:conclui|concluir|conclua|finaliza|finalizar|finalize)\s+#?\d+\b"), 0.98, "task-complete"),
            _IntentRule(IntentName.TASK_LIST, re.compile(r"\b(?:tarefas pendentes|minhas tarefas|lista(?:r)? tarefas|quais tarefas)\b|\bo que (?:eu )?(?:preciso|tenho que) fazer\b"), 0.97, "task-list"),
            _IntentRule(IntentName.TASK_CREATE, re.compile(r"^(?:adiciona|adicionar|adicione|cria|criar|crie|anota|anotar|anote|registre|registrar)\b.*\b(?:tarefa|lembrete)\b|^(?:nova|criar uma|adicionar uma)\s+tarefa\b|^(?:precisamos|preciso|tenho que|temos que)\s+\w+"), 0.96, "task-create"),
            _IntentRule(IntentName.AGENDA_CANCEL, re.compile(r"^(?:cancela|cancelar|cancele|remove|remover|remova)\b.*\b(?:compromisso|evento|agendamento)\b"), 0.98, "agenda-cancel"),
            _IntentRule(IntentName.AGENDA_CREATE, re.compile(r"^(?:agenda|agende|marque|marca|cria|criar|adicione|adiciona)\b.*\b(?:hoje|amanha|dia\s+\d{1,2}|\d{1,2}/\d{1,2})\b.*(?:\bas\b|\d{1,2}:\d{2})"), 0.97, "agenda-create"),
            _IntentRule(IntentName.DAILY_SUMMARY, re.compile(r"\b(?:resumo do dia|resuma meu dia|resumo de hoje|meu resumo de hoje)\b"), 0.98, "daily-summary"),
            _IntentRule(IntentName.AGENDA_QUERY, re.compile(r"\b(?:minha agenda|agenda de hoje|agenda hoje|compromissos hoje|meus compromissos|proximos compromissos)\b|\bo que (?:eu )?(?:tenho|temos) (?:para|pra) fazer hoje\b|\bo que (?:eu )?tenho hoje\b"), 0.96, "agenda-query"),
            _IntentRule(IntentName.SYSTEM_STATUS, re.compile(r"^(?:qual (?:e )?o )?status (?:da )?huli$|^status huli$|^huli (?:esta|ta) (?:ativa|funcionando|online)$"), 0.99, "huli-status"),
            _IntentRule(IntentName.TIME_QUERY, re.compile(r"^(?:que horas (?:sao|e)|qual (?:e )?a hora|qual (?:e )?o horario|horario agora|hora agora)(?: por favor)?$"), 0.99, "time-query"),
            _IntentRule(IntentName.SMALL_TALK, re.compile(r"^(?:(?:oi|ola|opa|e ai)(?: huli)?(?: bom dia| boa tarde| boa noite)?|(?:bom dia|boa tarde|boa noite)(?: huli)?|(?:como (?:voce|vc) (?:esta|ta)|tudo bem)(?: huli)?|(?:quem e voce|quem e a huli)(?: huli)?|(?:obrigado|obrigada|valeu|agradecido|agradecida)(?: huli)?|(?:tchau|ate logo|ate mais)(?: huli)?)$"), 0.95, "small-talk"),
        )

    def classify(self, text: str) -> IntentMatch:
        normalized = normalize_text(text)
        if not normalized:
            return IntentMatch(IntentName.UNKNOWN, 0.0, normalized, {"matched_rule": "empty"})
        normalized = re.sub(r"^huli\s+", "", normalized).strip()
        for rule in self._rules:
            match = rule.pattern.search(normalized)
            if match:
                metadata = {"matched_rule": rule.name}
                metadata.update({key: value for key, value in match.groupdict().items() if value is not None})
                return IntentMatch(rule.intent, rule.confidence, normalized, metadata)
        return IntentMatch(IntentName.UNKNOWN, 0.0, normalized, {"matched_rule": "none"})
