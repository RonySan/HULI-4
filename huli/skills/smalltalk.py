"""Conversação social básica e local da Huli."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from huli.core.contracts import KernelRequest, KernelResponse
from huli.personality import ConversationMode, PersonalityEngine
from huli.skills.parsing import normalize


class SmallTalkSkill:
    name = "smalltalk"
    intents = ("smalltalk",)

    def __init__(
        self,
        timezone_name: str,
        personality: PersonalityEngine | None = None,
    ) -> None:
        self.timezone = ZoneInfo(timezone_name)
        self.personality = personality

    def can_handle(self, request: KernelRequest) -> bool:
        return str(request.metadata.get("intent", "")) in self.intents

    def handle(self, request: KernelRequest) -> KernelResponse:
        if self.personality is not None:
            raw_mode = str(request.metadata.get("conversation_mode") or "casual")
            try:
                mode = ConversationMode(raw_mode)
            except ValueError:
                mode = ConversationMode.CASUAL
            answer = self.personality.smalltalk(
                text=request.text,
                username=str(request.metadata.get("username") or ""),
                mode=mode,
                is_followup=bool(request.metadata.get("conversation_followup")),
            )
            return KernelResponse(
                request_id=request.request_id,
                text=answer,
                handled_by=self.name,
            )

        text = normalize(request.text)
        username = str(request.metadata.get("username") or "").strip()
        suffix = (
            f", {username}"
            if username and username.casefold() != "visitante"
            else ""
        )
        if "quem e voce" in text or "quem e a huli" in text:
            answer = (
                "Sou a Huli, sua assistente pessoal. Nesta fase já consigo manter "
                "contexto curto, tarefas, agenda e algumas conversas locais."
            )
        elif "como voce esta" in text or "como vc ta" in text or "tudo bem" in text:
            answer = f"Estou operando normalmente{suffix}. E pronta para continuar."
        elif any(
            word in text
            for word in ("obrigado", "obrigada", "valeu", "agradecido", "agradecida")
        ):
            answer = f"Por nada{suffix}."
        elif any(word in text for word in ("tchau", "ate logo", "ate mais")):
            answer = f"Até mais{suffix}."
        else:
            hour = datetime.now(self.timezone).hour
            greeting = "Bom dia" if hour < 12 else "Boa tarde" if hour < 18 else "Boa noite"
            answer = f"{greeting}{suffix}. Estou por aqui."
        return KernelResponse(
            request_id=request.request_id,
            text=answer,
            handled_by=self.name,
        )
