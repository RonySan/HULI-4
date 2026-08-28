"""Conversação social local e contextual da Huli."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from huli.core.contracts import KernelRequest, KernelResponse
from huli.skills.parsing import normalize


class SmallTalkSkill:
    name = "smalltalk"
    intents = ("smalltalk",)

    def __init__(self, timezone_name: str) -> None:
        self.timezone = ZoneInfo(timezone_name)

    def can_handle(self, request: KernelRequest) -> bool:
        return str(request.metadata.get("intent", "")) in self.intents

    def handle(self, request: KernelRequest) -> KernelResponse:
        text = normalize(request.text)
        username = str(request.metadata.get("username") or "").strip()
        mode = str(request.metadata.get("conversation_mode") or "casual")
        signal = str(request.metadata.get("conversation_signal") or "neutral")
        turn = int(request.metadata.get("conversation_turn") or 1)
        suffix = (
            f", {username}"
            if username and username.casefold() != "visitante"
            else ""
        )

        if "o que significa huli" in text or "qual o significado de huli" in text:
            answer = (
                "HULI significa Humano Único Leal Inteligente. No dia a dia, meu nome é "
                "simplesmente Huli."
            )
        elif "quem e voce" in text or "quem e a huli" in text:
            answer = (
                "Sou a Huli, sua assistente pessoal. Já consigo manter contexto, tarefas, "
                "agenda, memória de longo prazo e conhecimento estruturado."
            )
        elif "o que voce consegue fazer" in text:
            answer = (
                "Hoje consigo conversar, manter contexto, organizar tarefas e agenda, lembrar "
                "informações, relacionar conhecimento e consultar o que foi registrado com fonte."
            )
        elif "como voce esta" in text or "como vc ta" in text or "tudo bem" in text:
            answer = self._status_answer(mode, suffix)
        elif any(
            word in text
            for word in ("obrigado", "obrigada", "valeu", "agradecido", "agradecida")
        ):
            answer = self._thanks_answer(mode, suffix)
        elif any(word in text for word in ("tchau", "ate logo", "ate mais")):
            answer = self._goodbye_answer(mode, suffix)
        else:
            answer = self._greeting(mode, suffix, turn)

        if signal == "frustration" and mode in {"serious", "risk"}:
            answer = f"{answer} Vou manter a conversa objetiva enquanto resolvemos isso."

        return KernelResponse(
            request_id=request.request_id,
            text=answer,
            handled_by=self.name,
        )

    def _greeting(self, mode: str, suffix: str, turn: int) -> str:
        hour = datetime.now(self.timezone).hour
        greeting = "Bom dia" if hour < 12 else "Boa tarde" if hour < 18 else "Boa noite"

        if mode == "professional":
            options = (
                f"{greeting}{suffix}. Estou pronta para seguir de forma objetiva.",
                f"{greeting}{suffix}. Podemos continuar com projetos, tarefas ou agenda.",
            )
        elif mode in {"serious", "risk"}:
            options = (
                f"{greeting}{suffix}. Estou aqui e vou manter tudo direto ao ponto.",
                f"{greeting}{suffix}. Pode seguir. Vou priorizar clareza e segurança.",
            )
        else:
            options = (
                f"{greeting}{suffix}. Estou por aqui.",
                f"{greeting}{suffix}. Huli online e pronta para a próxima missão.",
                f"{greeting}{suffix}. Pode mandar. Prometo reclamar só internamente.",
            )
        return options[(max(turn, 1) - 1) % len(options)]

    @staticmethod
    def _status_answer(mode: str, suffix: str) -> str:
        if mode == "professional":
            return f"Estou operando normalmente{suffix}. Pronta para continuar."
        if mode in {"serious", "risk"}:
            return f"Estou operacional{suffix}. Vou manter a resposta objetiva."
        return f"Tudo funcionando por aqui{suffix}. O que já é uma vitória estatística."

    @staticmethod
    def _thanks_answer(mode: str, suffix: str) -> str:
        if mode in {"professional", "serious", "risk"}:
            return f"Por nada{suffix}."
        return f"Por nada{suffix}. Pelo menos alguém aqui está valorizando o processamento."

    @staticmethod
    def _goodbye_answer(mode: str, suffix: str) -> str:
        if mode in {"serious", "risk"}:
            return f"Até mais{suffix}."
        return f"Até mais{suffix}. Vou ficar por aqui, dramaticamente imóvel em forma de código."
