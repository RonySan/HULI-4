"""Motor determinístico de personalidade e continuidade curta da Huli."""

from __future__ import annotations

from datetime import datetime
import re
from zoneinfo import ZoneInfo

from huli.brain.normalization import normalize_text
from huli.core.events import EventBus
from huli.personality.models import (
    ConversationDecision,
    ConversationMode,
    DEFAULT_PROFILE,
    PersonalityProfile,
)
from huli.security.privacy import is_private_journal_text


class PersonalityEngine:
    _PROFESSIONAL_PREFIXES = (
        "task.",
        "agenda.",
        "project.",
        "knowledge.",
        "memory.",
        "daily.",
        "morning.",
    )
    _RISK_INTENTS = {
        "memory.forget",
        "agenda.cancel",
        "agenda.complete",
        "journal.delete",
    }
    _PRIVATE_PREFIXES = ("journal.",)
    _SOCIAL_FOLLOWUPS = {
        "e voce",
        "e vc",
        "entendi",
        "beleza",
        "certo",
        "ok",
        "ta bom",
        "tudo certo",
    }

    def __init__(
        self,
        event_bus: EventBus,
        *,
        timezone_name: str = "America/Sao_Paulo",
        profile: PersonalityProfile = DEFAULT_PROFILE,
    ) -> None:
        self.events = event_bus
        self.profile = profile
        self.timezone = ZoneInfo(timezone_name)

    def decide(
        self,
        *,
        text: str,
        intent: str,
        last_intent: str | None = None,
        active_project: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> ConversationDecision:
        normalized = normalize_text(text)
        resolved_intent = intent
        is_followup = False
        reason = "default"

        if intent == "unknown" and self._asks_acronym_meaning(normalized):
            resolved_intent = "smalltalk"
            reason = "identity-question"
        elif intent == "unknown" and is_private_journal_text(text):
            resolved_intent = "journal.help"
            reason = "private-journal-fallback"
        elif (
            intent == "unknown"
            and active_project
            and self._looks_like_project_note(text, normalized, active_project)
        ):
            resolved_intent = "project.note"
            reason = "active-project-note"
        elif (
            intent == "unknown"
            and last_intent == "smalltalk"
            and normalized in self._SOCIAL_FOLLOWUPS
        ):
            resolved_intent = "smalltalk"
            is_followup = True
            reason = "social-followup"

        explicit_risk = bool((metadata or {}).get("high_risk"))
        if explicit_risk or resolved_intent in self._RISK_INTENTS:
            mode = ConversationMode.RISK
            reason = "risk"
        elif resolved_intent.startswith(self._PRIVATE_PREFIXES):
            mode = ConversationMode.PRIVATE
            reason = "private"
        elif re.search(
            r"\b(?:urgente|grave|serio|sério|falha critica|falha crítica|emergencia|emergência)\b",
            text,
            re.IGNORECASE,
        ):
            mode = ConversationMode.SERIOUS
            reason = "serious-signal"
        elif active_project or resolved_intent.startswith(self._PROFESSIONAL_PREFIXES):
            mode = ConversationMode.PROFESSIONAL
            if reason == "default":
                reason = "work-context"
        else:
            mode = ConversationMode.CASUAL
            if reason == "default":
                reason = "casual-default"

        return ConversationDecision(
            intent=resolved_intent,
            mode=mode,
            reason=reason,
            is_followup=is_followup,
        )

    def publish_decision(
        self,
        *,
        request_id: str,
        session_id: str,
        decision: ConversationDecision,
    ) -> None:
        self.events.publish(
            "conversation.mode.selected",
            {
                "request_id": request_id,
                "session_id": session_id,
                "intent": decision.intent,
                "mode": decision.mode.value,
                "reason": decision.reason,
                "is_followup": decision.is_followup,
            },
        )

    def smalltalk(
        self,
        *,
        text: str,
        username: str = "",
        mode: ConversationMode = ConversationMode.CASUAL,
        is_followup: bool = False,
    ) -> str:
        normalized = normalize_text(text)
        clean_user = " ".join(str(username or "").split()).strip()
        suffix = (
            f", {clean_user}"
            if clean_user and clean_user.casefold() != "visitante"
            else ""
        )

        if self._asks_acronym_meaning(normalized):
            return (
                f"HULI significa {self.profile.acronym_meaning}. "
                "No uso normal, meu nome é Huli."
            )

        if "quem e voce" in normalized or "quem e a huli" in normalized:
            return (
                "Sou a Huli, sua assistente pessoal. Mantenho contexto, memória e conhecimento "
                "estruturado sem inventar o que não está registrado."
            )

        if re.search(
            r"\b(?:vamos (?:comecar|iniciar)(?: os)? trabalhos|vamos trabalhar|podemos comecar)\b",
            normalized,
        ):
            return f"Certo{suffix}. Estou pronta para começar. Qual é a primeira prioridade?"

        if (
            "como voce esta" in normalized
            or "como vc ta" in normalized
            or re.fullmatch(r"(?:huli )?como (?:vai|esta|ta)(?: voce|vc)?(?: huli)?", normalized)
            or "tudo bem" in normalized
        ):
            if mode is ConversationMode.PROFESSIONAL:
                return f"Pronta para ajudar{suffix}. Podemos seguir com o trabalho."
            return f"Estou por aqui{suffix}. Como está seu dia?"

        if is_followup:
            if normalized in {"e voce", "e vc"}:
                return f"Continuo operacional{suffix}."
            return f"Certo{suffix}. Seguimos."

        if any(
            term in normalized
            for term in ("obrigado", "obrigada", "valeu", "agradecido", "agradecida")
        ):
            return f"Por nada{suffix}."

        if any(term in normalized for term in ("tchau", "ate logo", "ate mais")):
            return f"Até mais{suffix}."

        hour = datetime.now(self.timezone).hour
        greeting = "Bom dia" if hour < 12 else "Boa tarde" if hour < 18 else "Boa noite"
        return f"{greeting}{suffix}. Estou por aqui."

    @staticmethod
    def _asks_acronym_meaning(normalized: str) -> bool:
        return bool(
            re.search(
                r"\b(?:o que significa|qual o significado|significado de)\s+huli\b",
                normalized,
            )
        )

    @staticmethod
    def _looks_like_project_note(
        raw_text: str,
        normalized: str,
        active_project: str,
    ) -> bool:
        if raw_text.rstrip().endswith("?"):
            return False
        if re.match(
            r"^(?:o que|qual|como|quem|onde|quando|por que|porque)\b",
            normalized,
        ):
            return False
        project = normalize_text(active_project)
        if not project or project not in normalized:
            return False
        return bool(
            re.search(
                r"\b(?:e|eh|esta|foi|tem|possui|usa|precisa|depende|apresenta|serve|funciona|desenvolvido|desenvolvida)\b",
                normalized,
            )
        )


__all__ = ["PersonalityEngine"]
