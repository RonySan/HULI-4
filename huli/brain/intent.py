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
    DATE_QUERY = "date.query"
    MORNING_BRIEFING = "morning.briefing"
    AGENDA_QUERY = "agenda.query"
    AGENDA_CREATE = "agenda.create"
    AGENDA_CANCEL = "agenda.cancel"
    AGENDA_COMPLETE = "agenda.complete"
    TASK_CREATE = "task.create"
    TASK_LIST = "task.list"
    TASK_COMPLETE = "task.complete"
    DAILY_SUMMARY = "daily.summary"
    SMALL_TALK = "smalltalk"
    CONVERSATION_RECAP = "conversation.recap"
    JOURNAL_CREATE = "journal.create"
    JOURNAL_LIST = "journal.list"
    JOURNAL_SEARCH = "journal.search"
    JOURNAL_UPDATE = "journal.update"
    JOURNAL_DELETE = "journal.delete"
    JOURNAL_TRASH = "journal.trash"
    JOURNAL_RESTORE = "journal.restore"
    JOURNAL_HELP = "journal.help"
    PROJECT_SET = "project.set"
    PROJECT_QUERY = "project.query"
    PROJECT_NOTE = "project.note"
    MEMORY_REMEMBER = "memory.remember"
    MEMORY_RECALL = "memory.recall"
    MEMORY_LIST = "memory.list"
    MEMORY_FORGET = "memory.forget"
    KNOWLEDGE_DESCRIBE = "knowledge.describe"
    KNOWLEDGE_RELATION = "knowledge.relation"
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
            _IntentRule(
                IntentName.JOURNAL_RESTORE,
                re.compile(
                    r"^(?:restaure|restaurar|recupere|recuperar)\b.*\b(?:entrada|anotacao)\b.*\bdiario\b|^(?:restaure|restaurar|recupere|recuperar)\s+(?:a\s+)?#?\d+\s+(?:do|no)\s+(?:meu\s+)?diario$"
                ),
                0.995,
                "journal-restore",
            ),
            _IntentRule(
                IntentName.JOURNAL_TRASH,
                re.compile(
                    r"^(?:(?:mostre|liste|abra)\s+(?:a\s+)?lixeira\s+(?:do|no)\s+(?:meu\s+)?diario|lixeira\s+(?:do|no)\s+(?:meu\s+)?diario|(?:entradas|anotacoes)\s+apagadas\s+(?:do|no)\s+(?:meu\s+)?diario)$"
                ),
                0.99,
                "journal-trash",
            ),
            _IntentRule(
                IntentName.JOURNAL_DELETE,
                re.compile(
                    r"^(?:apague|apagar|exclua|excluir|remova|remover)\b.*\b(?:entrada|anotacao)\b.*\bdiario\b|^(?:apague|apagar|exclua|excluir|remova|remover)\s+(?:a\s+)?#?\d+\s+(?:do|no)\s+(?:meu\s+)?diario$"
                ),
                0.995,
                "journal-delete",
            ),
            _IntentRule(
                IntentName.JOURNAL_UPDATE,
                re.compile(
                    r"^(?:edite|editar|altere|alterar|corrija|corrigir)\b(?=.*\bdiario\b)(?=.*(?:\b(?:entrada|anotacao)\b|\b\d+\b)).+$"
                ),
                0.995,
                "journal-update",
            ),
            _IntentRule(
                IntentName.JOURNAL_SEARCH,
                re.compile(
                    r"^(?:(?:procure|buscar|busque|pesquise)\b.*\bdiario\b\s+(?:por|sobre)\s+.+|o que (?:eu )?escrevi (?:no|em) (?:meu )?diario sobre\s+.+|(?:encontre|mostre)\b.*\b(?:entradas|anotacoes)\b.*\bdiario\b\s+sobre\s+.+)$"
                ),
                0.995,
                "journal-search",
            ),
            _IntentRule(
                IntentName.JOURNAL_HELP,
                re.compile(
                    r"^(?:(?:como (?:eu )?uso|como funciona) (?:o )?(?:meu )?diario|(?:quero escrever|abrir|abra) (?:no )?(?:meu )?diario)$"
                ),
                0.99,
                "journal-help",
            ),
            _IntentRule(
                IntentName.JOURNAL_LIST,
                re.compile(
                    r"^(?:diario(?: (?:de|do) (?:hoje|ontem|\d{1,2}\s+\d{1,2}(?:\s+\d{2,4})?))?|meu diario(?: (?:de|do) (?:hoje|ontem|\d{1,2}\s+\d{1,2}(?:\s+\d{2,4})?))?|minhas (?:entradas|anotacoes) (?:do|no) diario|(?:mostre|liste|leia|abra|resuma) (?:o )?(?:meu )?diario(?: (?:de|do) (?:hoje|ontem|\d{1,2}\s+\d{1,2}(?:\s+\d{2,4})?))?|o que (?:eu )?escrevi (?:hoje|ontem)?\s*(?:no|em) (?:meu )?diario)$"
                ),
                0.99,
                "journal-list",
            ),
            _IntentRule(
                IntentName.JOURNAL_CREATE,
                re.compile(
                    r"^(?:diario\s+(?!de\s+(?:hoje|ontem)$)\S.+|(?:anote|anota|registre|registra|escreva|escreve|salve|guarde)\b.*\b(?:meu )?diario\b\s+\S.+)$"
                ),
                0.995,
                "journal-create",
            ),
            _IntentRule(
                IntentName.KNOWLEDGE_RELATION,
                re.compile(
                    r"^(?:quem (?:desenvolve|desenvolveu) .+|onde .+ (?:esta|fica) hospedado|qual servidor hospeda .+|do que .+ depende|(?:a que|a quem) .+ pertence|de quem .+ (?:e|eh) cliente)$"
                ),
                0.995,
                "knowledge-relation",
            ),
            _IntentRule(
                IntentName.KNOWLEDGE_DESCRIBE,
                re.compile(
                    r"^(?:o que voce sabe (?:sobre|de)|fale (?:sobre|do|da)|informacoes (?:sobre|de))\s+.+$"
                ),
                0.99,
                "knowledge-describe",
            ),
            _IntentRule(
                IntentName.MEMORY_FORGET,
                re.compile(
                    r"^(?:esqueca|esquecer|apague|remova|remove)\b.*(?:memoria|lembra|#?\d+)|^(?:esqueca|esquecer)\s+.+$"
                ),
                0.99,
                "memory-forget",
            ),
            _IntentRule(
                IntentName.MEMORY_LIST,
                re.compile(
                    r"^(?:minhas memorias|liste (?:as )?(?:minhas )?memorias|mostrar? (?:as )?(?:minhas )?memorias|o que voce lembra)$"
                ),
                0.99,
                "memory-list",
            ),
            _IntentRule(
                IntentName.MEMORY_RECALL,
                re.compile(
                    r"^(?:o que voce lembra (?:sobre|de)|voce lembra (?:sobre|de)|lembra (?:sobre|de))\s+.+$"
                ),
                0.99,
                "memory-recall",
            ),
            _IntentRule(
                IntentName.MEMORY_REMEMBER,
                re.compile(
                    r"^(?:lembre|lembra|guarde|memorize|grave|anote na memoria)\s+(?:que\s+)?\S.+$"
                ),
                0.99,
                "memory-remember",
            ),
            _IntentRule(
                IntentName.PROJECT_SET,
                re.compile(
                    r"^(?:vamos falar (?:do|sobre o)|estamos no|mude para o|usar o) projeto\b|^projeto atual (?:e|eh)\b|^defina (?:o )?projeto\b"
                ),
                0.99,
                "project-set",
            ),
            _IntentRule(
                IntentName.PROJECT_QUERY,
                re.compile(
                    r"\b(?:qual projeto (?:estamos|esta ativo)|projeto ativo)\b|\b(?:status|situacao|andamento|como esta)\b.*\bprojeto\b|\bprojeto\b.*\b(?:status|situacao|andamento)\b"
                ),
                0.98,
                "project-query",
            ),
            _IntentRule(
                IntentName.CONVERSATION_RECAP,
                re.compile(
                    r"^(?:o que (?:nos |a gente )?(?:conversamos|conversou|falamos|falou)(?: mais cedo| hoje| anteriormente| ate agora)?|sobre o que (?:nos |a gente )?(?:conversamos|conversou|falamos|falou)(?: mais cedo| hoje)?|(?:relembre|resuma) (?:a |nossa )?conversa(?: de hoje| ate agora)?|o que foi conversado(?: mais cedo| hoje)?)$"
                ),
                0.99,
                "conversation-recap",
            ),
            _IntentRule(
                IntentName.TASK_COMPLETE,
                re.compile(
                    r"^(?:conclui|concluir|conclua|finaliza|finalizar|finalize|marque|marca)\b.*\btarefa\b|^(?:conclui|concluir|conclua|finaliza|finalizar|finalize)\s+#?\d+\b"
                ),
                0.98,
                "task-complete",
            ),
            _IntentRule(
                IntentName.TASK_LIST,
                re.compile(
                    r"\b(?:tarefas pendentes|minhas tarefas|lista(?:r)? tarefas|quais tarefas)\b|\bo que (?:eu )?(?:preciso|tenho que) fazer\b"
                ),
                0.97,
                "task-list",
            ),
            _IntentRule(
                IntentName.TASK_COMPLETE,
                re.compile(r"^(?!.*\b(?:nao|nunca|ainda|se|talvez)\b).{3,}?\s+(?:verificad[oa]|concluid[oa]|finalizad[oa]|resolvid[oa])(?:\s+huli)?$"),
                0.96,
                "task-complete-natural",
            ),
            _IntentRule(
                IntentName.TASK_CREATE,
                re.compile(
                    r"^(?:adiciona|adicionar|adicione|cria|criar|crie|anota|anotar|anote|registre|registrar)\b.*\b(?:tarefa|lembrete)\b|^(?:nova|criar uma|adicionar uma)\s+tarefa\b|^(?:precisamos|preciso|tenho que|temos que)\s+\w+"
                ),
                0.96,
                "task-create",
            ),
            _IntentRule(
                IntentName.AGENDA_CANCEL,
                re.compile(
                    r"^(?:cancela|cancelar|cancele|remove|remover|remova)\b.*\b(?:compromisso|evento|agendamento)\b"
                ),
                0.98,
                "agenda-cancel",
            ),
            _IntentRule(
                IntentName.AGENDA_COMPLETE,
                re.compile(
                    r"^(?:pode\s+)?(?:conclui|concluir|conclua|finaliza|finalizar|finalize|realiza|realizar|realize|marque|marca)\b.*\b(?:compromisso|evento|agendamento)\b"
                ),
                0.985,
                "agenda-complete",
            ),
            _IntentRule(
                IntentName.AGENDA_CREATE,
                re.compile(
                    r"^(?:agenda|agende|marque|marca|cria|criar|adicione|adiciona)\b.*(?:\bas\s+(?:\d{1,2}(?::\d{2})?|(?:uma?|duas?|tres|quatro|cinco|seis|sete|oito|nove|dez|onze|doze|treze|catorze|quatorze|quinze|dezesseis|dezessete|dezoito|dezenove|vinte|vinte e uma|vinte e duas|vinte e tres))\s*(?:h|horas?)?\b|\b\d{1,2}:\d{2}\b)"
                ),
                0.97,
                "agenda-create",
            ),
            _IntentRule(
                IntentName.DAILY_SUMMARY,
                re.compile(
                    r"\b(?:resumo do dia|resuma meu dia|resumo de hoje|meu resumo de hoje)\b"
                ),
                0.98,
                "daily-summary",
            ),
            _IntentRule(
                IntentName.AGENDA_QUERY,
                re.compile(
                    r"^(?:agenda|agendas|minha agenda|nossa agenda)$|\b(?:(?:minha|nossa) agenda|agenda (?:de |para |pra )?(?:hoje|amanha|esta noite|essa noite)|compromissos (?:(?:de|para|pra) )?(?:hoje|amanha|esta noite|essa noite)|meus compromissos|proximos compromissos)\b|\bo que (?:eu )?(?:tenho|temos) (?:para|pra) fazer (?:hoje|amanha)\b|\bo que (?:eu )?temos? na agenda\b|\bo que (?:eu )?tenho (?:hoje|amanha)\b|\btemos compromissos (?:(?:para|pra) )?(?:hoje|amanha)\b"
                ),
                0.96,
                "agenda-query",
            ),
            _IntentRule(
                IntentName.SYSTEM_STATUS,
                re.compile(
                    r"^(?:qual (?:e )?o )?status (?:da )?huli$|^status huli$|^huli (?:esta|ta) (?:ativa|funcionando|online)$"
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
                IntentName.DATE_QUERY,
                re.compile(
                    r"^(?:que dia (?:e|eh) hoje|qual (?:e )?a data(?: de hoje| hoje)?|data de hoje|qual dia (?:e|eh) hoje|em que dia estamos)(?: por favor)?$"
                ),
                0.99,
                "date-query",
            ),
            _IntentRule(
                IntentName.MORNING_BRIEFING,
                re.compile(r"^bom dia(?: huli)?$"),
                0.995,
                "morning-briefing",
            ),
            _IntentRule(
                IntentName.SMALL_TALK,
                re.compile(
                    r"^(?:(?:oi|ola|opa|e ai)(?: huli)?(?: bom dia| boa tarde| boa noite)?|(?:bom dia|boa tarde|boa noite)(?: huli)?|(?:como (?:voce|vc) (?:esta|ta)|tudo bem)(?: huli)?|(?:quem e voce|quem e a huli)(?: huli)?|(?:obrigado|obrigada|valeu|agradecido|agradecida)(?: huli)?|(?:tchau|ate logo|ate mais)(?: huli)?|(?:(?:ok|certo|beleza) )?(?:entao )?(?:vamos (?:comecar|iniciar)(?: os)? trabalhos(?: de hoje)?|vamos trabalhar|podemos comecar))$"
                ),
                0.95,
                "small-talk",
            ),
        )

    def classify(self, text: str) -> IntentMatch:
        normalized = normalize_text(text)
        normalized = re.sub(r"\bminah\b", "minha", normalized)
        normalized = re.sub(r"\bpar ahoje\b", "para hoje", normalized)
        if not normalized:
            return IntentMatch(
                IntentName.UNKNOWN,
                0.0,
                normalized,
                {"matched_rule": "empty"},
            )
        normalized = re.sub(r"^huli\s+", "", normalized).strip()
        if re.fullmatch(r"como (?:vai|esta|ta)(?: voce|vc)?(?: huli)?", normalized):
            return IntentMatch(IntentName.SMALL_TALK, 0.97, normalized, {"matched_rule": "social-how-are-you"})
        if re.search(r"\bo que (?:eu )?(?:tenho|temos) (?:pra|para) (?:hoje|amanha|esta tarde|essa tarde)\b", normalized):
            return IntentMatch(IntentName.AGENDA_QUERY, 0.97, normalized, {"matched_rule": "natural-agenda-period"})
        for rule in self._rules:
            if rule.name == "task-complete-natural" and "?" in text:
                continue
            match = rule.pattern.search(normalized)
            if match:
                metadata = {"matched_rule": rule.name}
                metadata.update(
                    {
                        key: value
                        for key, value in match.groupdict().items()
                        if value is not None
                    }
                )
                return IntentMatch(rule.intent, rule.confidence, normalized, metadata)
        return IntentMatch(
            IntentName.UNKNOWN,
            0.0,
            normalized,
            {"matched_rule": "none"},
        )
