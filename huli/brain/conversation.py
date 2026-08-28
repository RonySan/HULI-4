"""Estado conversacional, modos e sinais de tom da Huli."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import re
from threading import RLock

from huli.brain.normalization import normalize_text


class ConversationMode(StrEnum):
    AUTO = "auto"
    CASUAL = "casual"
    PROFESSIONAL = "professional"
    SERIOUS = "serious"
    RISK = "risk"


class ConversationSignal(StrEnum):
    NEUTRAL = "neutral"
    POSITIVE = "positive"
    GRATITUDE = "gratitude"
    FRUSTRATION = "frustration"
    URGENCY = "urgency"
    RISK = "risk"


@dataclass(frozen=True, slots=True)
class ConversationSnapshot:
    session_id: str
    mode: ConversationMode
    override: ConversationMode | None
    signal: ConversationSignal
    humor_allowed: bool
    turn_count: int


@dataclass(slots=True)
class _ConversationState:
    mode: ConversationMode = ConversationMode.CASUAL
    override: ConversationMode | None = None
    signal: ConversationSignal = ConversationSignal.NEUTRAL
    turn_count: int = 0


class ConversationEngine:
    """Mantém estilo e sinais por sessão sem alterar fatos ou memória."""

    _RISK_PATTERN = re.compile(
        r"\b(?:senha|password|token|api key|chave de api|chave privada|segredo|"
        r"formatar|formatacao|apagar tudo|excluir tudo|deletar tudo|resetar|"
        r"transferir dinheiro|pagamento|pix)\b"
    )
    _URGENCY_PATTERN = re.compile(
        r"\b(?:urgente|urgencia|imediato|imediatamente|agora mesmo|emergencia|critico|critica)\b"
    )
    _FRUSTRATION_PATTERN = re.compile(
        r"\b(?:nao funciona|nao esta funcionando|nao ta funcionando|deu errado|continua errado|"
        r"continua dando erro|erro de novo|falhou|quebrou|travou|problema)\b"
    )
    _GRATITUDE_PATTERN = re.compile(
        r"\b(?:obrigado|obrigada|valeu|agradecido|agradecida|perfeito|otimo|excelente)\b"
    )
    _POSITIVE_PATTERN = re.compile(r"\b(?:bom|legal|bacana|top|show|gostei|adorei)\b")
    _PROFESSIONAL_PATTERN = re.compile(
        r"\b(?:cliente|relatorio|orcamento|projeto|tarefa|agenda|compromisso|servidor|"
        r"sistema|banco de dados|deploy|producao|empresa|ordem de servico)\b"
    )

    def __init__(self) -> None:
        self._states: dict[str, _ConversationState] = {}
        self._lock = RLock()

    def analyze(self, session_id: str, text: str, intent: str) -> ConversationSnapshot:
        session = self._normalize_session_id(session_id)
        normalized = normalize_text(text)
        signal = self._detect_signal(normalized)
        with self._lock:
            state = self._states.setdefault(session, _ConversationState())
            state.signal = signal
            state.turn_count += 1
            state.mode = self._resolve_mode(
                normalized,
                intent,
                signal,
                state.override,
            )
            return self._snapshot_unlocked(session, state)

    def set_mode(self, session_id: str, mode: ConversationMode | str) -> ConversationSnapshot:
        session = self._normalize_session_id(session_id)
        resolved = self.parse_mode(mode)
        with self._lock:
            state = self._states.setdefault(session, _ConversationState())
            if resolved is ConversationMode.AUTO:
                state.override = None
                state.mode = ConversationMode.CASUAL
            else:
                state.override = resolved
                state.mode = resolved
            return self._snapshot_unlocked(session, state)

    def snapshot(self, session_id: str) -> ConversationSnapshot:
        session = self._normalize_session_id(session_id)
        with self._lock:
            state = self._states.setdefault(session, _ConversationState())
            return self._snapshot_unlocked(session, state)

    def clear(self, session_id: str) -> None:
        session = self._normalize_session_id(session_id)
        with self._lock:
            self._states.pop(session, None)

    def fallback_text(self, snapshot: ConversationSnapshot) -> str:
        if snapshot.mode is ConversationMode.RISK:
            return (
                "Essa solicitação parece sensível. Não vou executar nada sem uma "
                "capacidade explícita e as confirmações de segurança necessárias."
            )
        if snapshot.signal is ConversationSignal.URGENCY:
            return (
                "Entendi que isso é urgente, mas ainda não reconheci uma capacidade segura "
                "para executar essa solicitação."
            )
        if snapshot.signal is ConversationSignal.FRUSTRATION:
            return (
                "Entendi que algo não está funcionando. Ainda não reconheci uma ação segura "
                "nessa frase, então não vou fingir que executei alguma coisa."
            )
        if snapshot.mode is ConversationMode.PROFESSIONAL:
            return "Não reconheci uma capacidade segura para executar essa solicitação."
        return "Ainda não reconheço uma capacidade segura para essa solicitação."

    @classmethod
    def parse_mode(cls, value: ConversationMode | str) -> ConversationMode:
        if isinstance(value, ConversationMode):
            return value
        normalized = normalize_text(str(value or ""))
        aliases = {
            "auto": ConversationMode.AUTO,
            "automatico": ConversationMode.AUTO,
            "casual": ConversationMode.CASUAL,
            "profissional": ConversationMode.PROFESSIONAL,
            "professional": ConversationMode.PROFESSIONAL,
            "serio": ConversationMode.SERIOUS,
            "serious": ConversationMode.SERIOUS,
            "risco": ConversationMode.RISK,
            "seguro": ConversationMode.RISK,
            "risk": ConversationMode.RISK,
        }
        try:
            return aliases[normalized]
        except KeyError as exc:
            raise ValueError(
                "Modo inválido. Use automático, casual, profissional, sério ou risco."
            ) from exc

    def _resolve_mode(
        self,
        normalized: str,
        intent: str,
        signal: ConversationSignal,
        override: ConversationMode | None,
    ) -> ConversationMode:
        if signal is ConversationSignal.RISK:
            return ConversationMode.RISK
        if override is not None:
            return override
        if signal in {ConversationSignal.URGENCY, ConversationSignal.FRUSTRATION}:
            return ConversationMode.SERIOUS
        if intent == "smalltalk":
            return ConversationMode.CASUAL
        if intent.startswith(("task.", "agenda.", "project.", "daily.", "knowledge.")):
            return ConversationMode.PROFESSIONAL
        if self._PROFESSIONAL_PATTERN.search(normalized):
            return ConversationMode.PROFESSIONAL
        return ConversationMode.CASUAL

    def _detect_signal(self, normalized: str) -> ConversationSignal:
        if self._RISK_PATTERN.search(normalized):
            return ConversationSignal.RISK
        if self._URGENCY_PATTERN.search(normalized):
            return ConversationSignal.URGENCY
        if self._FRUSTRATION_PATTERN.search(normalized):
            return ConversationSignal.FRUSTRATION
        if self._GRATITUDE_PATTERN.search(normalized):
            return ConversationSignal.GRATITUDE
        if self._POSITIVE_PATTERN.search(normalized):
            return ConversationSignal.POSITIVE
        return ConversationSignal.NEUTRAL

    @staticmethod
    def _snapshot_unlocked(
        session_id: str,
        state: _ConversationState,
    ) -> ConversationSnapshot:
        humor_allowed = state.mode not in {ConversationMode.SERIOUS, ConversationMode.RISK}
        return ConversationSnapshot(
            session_id=session_id,
            mode=state.mode,
            override=state.override,
            signal=state.signal,
            humor_allowed=humor_allowed,
            turn_count=state.turn_count,
        )

    @staticmethod
    def _normalize_session_id(session_id: str) -> str:
        normalized = str(session_id or "default").strip() or "default"
        if len(normalized) > 128:
            raise ValueError("session_id pode ter no máximo 128 caracteres.")
        return normalized


__all__ = [
    "ConversationEngine",
    "ConversationMode",
    "ConversationSignal",
    "ConversationSnapshot",
]
