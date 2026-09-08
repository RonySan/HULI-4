"""Classificação determinística de intenções fundamentais da Huli."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import re
from typing import Mapping

from huli.brain.normalization import normalize_text


class IntentName(StrEnum):
    SYSTEM_STATUS = "system.status"
    COMPUTER_HEALTH = "computer.health"
    CALCULATOR_QUERY = "calculator.query"
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
    SHOPPING_ADD = "shopping.add"
    SHOPPING_LIST = "shopping.list"
    SHOPPING_COMPLETE = "shopping.complete"
    TIMER_CREATE = "timer.create"
    TIMER_LIST = "timer.list"
    TIMER_CANCEL = "timer.cancel"
    HABIT_CREATE = "habit.create"
    HABIT_LIST = "habit.list"
    HABIT_COMPLETE = "habit.complete"
    FOCUS_START = "focus.start"
    FOCUS_NEXT = "focus.next"
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
    APP_OPEN = "app.open"
    MEDIA_FAVORITES = "media.favorites"
    MEDIA_PLAY = "media.play"
    MEDIA_PAUSE = "media.pause"
    MEDIA_STOP = "media.stop"
    MEDIA_NEXT = "media.next"
    MEDIA_PREVIOUS = "media.previous"
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
                IntentName.HABIT_COMPLETE,
                re.compile(
                    r"^(?:(?:marque|marcar)\s+(?:o\s+)?habito\s+.+\s+como\s+(?:feito|concluido)|(?:conclua|concluir|complete|completar|cumpri|fiz)\s+(?:o\s+)?habito\s+.+)$"
                ),
                0.995,
                "habit-complete",
            ),
            _IntentRule(
                IntentName.HABIT_LIST,
                re.compile(
                    r"^(?:(?:meus|os meus)\s+habitos|habitos\s+de\s+hoje|(?:como estao|mostre|liste|listar)\s+(?:os\s+)?(?:meus\s+)?habitos|progresso\s+(?:dos\s+)?(?:meus\s+)?habitos)$"
                ),
                0.99,
                "habit-list",
            ),
            _IntentRule(
                IntentName.HABIT_CREATE,
                re.compile(
                    r"^(?:(?:crie|criar|adicione|adicionar|cadastre|cadastrar)\s+(?:um\s+)?habitos?\s+(?:para\s+)?\S.+|novo\s+habito\s+.+)$"
                ),
                0.995,
                "habit-create",
            ),
            _IntentRule(
                IntentName.FOCUS_NEXT,
                re.compile(
                    r"^(?:qual (?:e )?a minha prioridade agora|no que (?:eu )?devo focar agora|o que (?:eu )?faco agora|qual (?:e )?o proximo passo)$"
                ),
                0.99,
                "focus-next",
            ),
            _IntentRule(
                IntentName.FOCUS_START,
                re.compile(
                    r"^(?:(?:inicie|iniciar|comece|comecar|ative|ativar)\s+(?:uma\s+)?(?:sessao\s+de\s+)?foco(?:\s+(?:por|de|para)\s+.+)?|(?:inicie|iniciar|comece|comecar)\s+(?:um\s+)?pomodoro(?:\s+.+)?)$"
                ),
                0.99,
                "focus-start",
            ),
            _IntentRule(
                IntentName.TIMER_CANCEL,
                re.compile(
                    r"^(?:cancele|cancelar|pare|parar)\s+(?:o\s+)?(?:timer|temporizador|cronometro)(?:\s+(?:numero\s*)?#?\d+)$"
                ),
                0.995,
                "timer-cancel",
            ),
            _IntentRule(
                IntentName.TIMER_LIST,
                re.compile(
                    r"^(?:(?:quais|liste|listar|mostre|mostrar)\s+(?:os\s+)?(?:timers|temporizadores|cronometros)(?:\s+ativos)?|(?:timers|temporizadores|cronometros)\s+ativos)$"
                ),
                0.99,
                "timer-list",
            ),
            _IntentRule(
                IntentName.TIMER_CREATE,
                re.compile(
                    r"^(?:(?:crie|criar|inicie|iniciar|coloque|colocar)?\s*(?:um\s+)?(?:timer|temporizador|cronometro)\s+(?:de|para)\s+.+|me\s+avise\s+em\s+.+\b(?:segundos?|minutos?|horas?)\b.*)$"
                ),
                0.99,
                "timer-create",
            ),
            _IntentRule(
                IntentName.COMPUTER_HEALTH,
                re.compile(
                    r"^(?:como (?:esta|ta)|verifique|verificar|mostre|qual (?:e )?o estado d[oa]) (?:meu |o )?(?:computador|pc|notebook)(?: hoje)?$|^(?:saude|desempenho|uso) (?:do|de meu|do meu) (?:computador|pc|notebook)$"
                ),
                0.99,
                "computer-health",
            ),
            _IntentRule(
                IntentName.CALCULATOR_QUERY,
                re.compile(
                    r"^(?:calcule|calcular|calcula|quanto (?:e|eh|da)|qual (?:e )?o resultado de|faca a conta|(?:some|soma|somar|subtraia|subtrair|multiplique|multiplicar|divida|dividir)(?: para mim)?)\s+.+$"
                ),
                0.99,
                "calculator-query",
            ),
            _IntentRule(
                IntentName.SHOPPING_COMPLETE,
                re.compile(
                    r"^(?:(?:eu )?(?:ja )?comprei\s+.+|(?:marque|marcar)\s+.+\s+como\s+comprad[oa]|(?:retire|retirar|remova|remover)\s+.+\s+(?:da|de)\s+(?:minha\s+)?lista\s+de\s+compras)$"
                ),
                0.995,
                "shopping-complete",
            ),
            _IntentRule(
                IntentName.SHOPPING_LIST,
                re.compile(
                    r"^(?:(?:minha\s+)?lista\s+de\s+compras|(?:mostre|mostrar|liste|listar)\s+(?:a\s+)?(?:minha\s+)?lista\s+de\s+compras|o que (?:ainda )?(?:falta|preciso|temos que) comprar)$"
                ),
                0.99,
                "shopping-list",
            ),
            _IntentRule(
                IntentName.SHOPPING_ADD,
                re.compile(
                    r"^(?:(?:adicione|adicionar|adiciona|coloque|colocar|inclua|incluir)\s+.+\s+(?:na|a)\s+(?:minha\s+)?lista\s+de\s+compras|(?:lista\s+de\s+compras)\s*.+|(?:eu\s+)?preciso\s+comprar\s+.+)$"
                ),
                0.99,
                "shopping-add",
            ),
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
                    r"^(?:agenda|agendas|minha agenda|nossa agenda)$|^(?:voce sabe )?quando (?:eu )?(?:tenho|tem|temos) compromissos (?:este|esse|neste|nesse) (?:mes|semana)$|\b(?:(?:minha|nossa) agenda|agenda (?:de |para |pra )?(?:hoje|amanha|esta noite|essa noite|(?:este|esse|neste) (?:mes|semana))|compromissos (?:(?:de|para|pra) )?(?:hoje|amanha|esta noite|essa noite|(?:deste|desse|neste) (?:mes|semana))|meus compromissos|proximos compromissos)\b|\bo que (?:eu )?(?:tenho|temos) (?:para|pra) fazer (?:hoje|amanha)\b|\bo que (?:eu )?temos? na agenda\b|\bo que (?:eu )?tenho (?:hoje|amanha)\b|\btemos compromissos (?:(?:para|pra) )?(?:hoje|amanha)\b"
                ),
                0.96,
                "agenda-query",
            ),
            _IntentRule(
                IntentName.MEDIA_FAVORITES,
                re.compile(
                    r"^(?:abra|abre|abrir)\s+(?:(?:o|a)\s+)?(?:spotify|esportes? pai|esporte fai|esportifai|spot fai|spot fire)\s+e\s+(?:pode\s+)?(?:toca|tocar|toque|coloca|colocar|coloque)\s+(?:as\s+)?(?:minhas\s+)?(?:(?:musicas?|cancoes?)\s+)?(?:favoritas|curtidas)$"
                ),
                0.999,
                "media-open-favorites",
            ),
            _IntentRule(
                IntentName.APP_OPEN,
                re.compile(
                    r"^(?:abra|abre|abrir|inicie|iniciar|execute|executar|rode|rodar)\s+(?!(?:(?:o|a)\s+)?(?:link|site|pagina|arquivo|pasta|documento)\b)(?:(?:o|a)\s+)?(?:(?:programa|aplicativo|app)\s+)?\S.+$"
                ),
                0.98,
                "app-open",
            ),
            _IntentRule(
                IntentName.MEDIA_FAVORITES,
                re.compile(
                    r"^(?:pode\s+)?(?:toca|tocar|toque|coloca|colocar|coloque)\s+(?:as\s+)?(?:minhas\s+)?(?:(?:musicas?|cancoes?)\s+)?(?:favoritas|curtidas)(?:\s+(?:do|no)\s+spotify)?$"
                ),
                0.995,
                "media-favorites",
            ),
            _IntentRule(
                IntentName.MEDIA_NEXT,
                re.compile(
                    r"^(?:pode\s+)?(?:proxima(?:\s+musica)?|passe?\s+para\s+a\s+proxima|pular?\s+musica)$"
                ),
                0.99,
                "media-next",
            ),
            _IntentRule(
                IntentName.MEDIA_PREVIOUS,
                re.compile(
                    r"^(?:pode\s+)?(?:musica\s+anterior|volte?\s+(?:a|para a)\s+musica\s+anterior)$"
                ),
                0.99,
                "media-previous",
            ),
            _IntentRule(
                IntentName.MEDIA_PAUSE,
                re.compile(
                    r"^(?:pode\s+)?(?:pausa|pausar|pause)\s*(?:a\s+)?(?:musica|reproducao|spotify)?$"
                ),
                0.99,
                "media-pause",
            ),
            _IntentRule(
                IntentName.MEDIA_STOP,
                re.compile(
                    r"^(?:pode\s+)?(?:pare|parar|encerre|encerrar)\s+(?:a\s+)?(?:musica|reproducao|spotify)$"
                ),
                0.99,
                "media-stop",
            ),
            _IntentRule(
                IntentName.MEDIA_PLAY,
                re.compile(
                    r"^(?:pode\s+)?(?:toca|tocar|toque|continue|continuar|retome|retomar)\s*(?:a\s+)?(?:musica|reproducao|spotify)?$"
                ),
                0.99,
                "media-play",
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
        # O nome é vocativo, não parte do comando. Aceitar somente as formas
        # reais evita transformar palavras comuns ("olhe", "link") no nome.
        vocative = r"(?:huli|ruli|ruly|ru li)"
        normalized = re.sub(rf"^{vocative}\s+", "", normalized).strip()
        # Pedidos educados são enquadramento da frase e não uma intenção.
        # A remoção é limitada ao começo para não alterar títulos ou conteúdo.
        normalized = re.sub(
            r"^(?:(?:por favor|por gentileza|voce pode|pode por favor|pode)\s+)+",
            "",
            normalized,
        ).strip()
        normalized = re.sub(rf"^{vocative}\s+", "", normalized).strip()
        candidates = [normalized]
        without_trailing_vocative = re.sub(
            rf"\s+{vocative}$",
            "",
            normalized,
        ).strip()
        if without_trailing_vocative and without_trailing_vocative != normalized:
            candidates.append(without_trailing_vocative)

        for candidate in candidates:
            if re.fullmatch(
                r"como (?:vai|esta|ta)(?: voce|vc)?(?: huli)?",
                candidate,
            ):
                return IntentMatch(
                    IntentName.SMALL_TALK,
                    0.97,
                    candidate,
                    {"matched_rule": "social-how-are-you"},
                )
            if re.search(
                r"\bo que (?:eu )?(?:tenho|temos) (?:pra|para) "
                r"(?:hoje|amanha|esta tarde|essa tarde)\b",
                candidate,
            ):
                return IntentMatch(
                    IntentName.AGENDA_QUERY,
                    0.97,
                    candidate,
                    {"matched_rule": "natural-agenda-period"},
                )
            for rule in self._rules:
                if rule.name == "task-complete-natural" and "?" in text:
                    continue
                match = rule.pattern.search(candidate)
                if match:
                    metadata = {"matched_rule": rule.name}
                    metadata.update(
                        {
                            key: value
                            for key, value in match.groupdict().items()
                            if value is not None
                        }
                    )
                    return IntentMatch(
                        rule.intent,
                        rule.confidence,
                        candidate,
                        metadata,
                    )
        return IntentMatch(
            IntentName.UNKNOWN,
            0.0,
            normalized,
            {"matched_rule": "none"},
        )
