"""Estado e comandos de voz da interface local."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from huli.brain.normalization import normalize_text
from huli.voice.service import VoiceService


class VoiceCommand(StrEnum):
    NONE = "none"
    STATUS = "status"
    ENABLE = "enable"
    DISABLE = "disable"
    LISTEN = "listen"
    CONTINUOUS = "continuous"
    STOP = "stop"


def parse_voice_command(text: str) -> VoiceCommand:
    normalized = normalize_text(text)
    mapping = {
        "voz": VoiceCommand.STATUS,
        "status da voz": VoiceCommand.STATUS,
        "status voz": VoiceCommand.STATUS,
        "ativar voz": VoiceCommand.ENABLE,
        "ligar voz": VoiceCommand.ENABLE,
        "voz ligar": VoiceCommand.ENABLE,
        "fale comigo": VoiceCommand.ENABLE,
        "desativar voz": VoiceCommand.DISABLE,
        "desligar voz": VoiceCommand.DISABLE,
        "voz desligar": VoiceCommand.DISABLE,
        "ouvir": VoiceCommand.LISTEN,
        "me ouca": VoiceCommand.LISTEN,
        "escute": VoiceCommand.LISTEN,
        "modo voz": VoiceCommand.CONTINUOUS,
        "conversa por voz": VoiceCommand.CONTINUOUS,
        "conversar por voz": VoiceCommand.CONTINUOUS,
        "parar voz": VoiceCommand.STOP,
        "parar de ouvir": VoiceCommand.STOP,
        "voltar ao teclado": VoiceCommand.STOP,
    }
    return mapping.get(normalized, VoiceCommand.NONE)


@dataclass(slots=True)
class VoiceSession:
    service: VoiceService
    auto_speak: bool = False
    continuous: bool = False

    def status_text(self) -> str:
        capabilities = self.service.capabilities()
        if not capabilities.output_available:
            return f"Voz indisponível. {capabilities.detail}"
        output = "ligada" if self.auto_speak else "desligada"
        mode = "contínuo" if self.continuous else "comando único"
        return (
            f"Voz local disponível ({capabilities.provider}). "
            f"Respostas faladas: {output}. Modo: {mode}."
        )

    def can_speak_response(self, intent: str) -> bool:
        return self.auto_speak and not intent.startswith("journal.")
