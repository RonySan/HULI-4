"""Estado e comandos de voz da interface local."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import re

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
    normalized = re.sub(r"^huli\s+|\s+huli$", "", normalized).strip()
    mapping = {
        "voz": VoiceCommand.STATUS,
        "status da voz": VoiceCommand.STATUS,
        "status voz": VoiceCommand.STATUS,
        "ativar voz": VoiceCommand.ENABLE,
        "ativar a voz": VoiceCommand.ENABLE,
        "ligar voz": VoiceCommand.ENABLE,
        "ligar a voz": VoiceCommand.ENABLE,
        "voz ligar": VoiceCommand.ENABLE,
        "fale comigo": VoiceCommand.ENABLE,
        "desativar voz": VoiceCommand.DISABLE,
        "desativar a voz": VoiceCommand.DISABLE,
        "desligar voz": VoiceCommand.DISABLE,
        "desligar a voz": VoiceCommand.DISABLE,
        "voz desligar": VoiceCommand.DISABLE,
        "ouvir": VoiceCommand.LISTEN,
        "me ouca": VoiceCommand.LISTEN,
        "escute": VoiceCommand.LISTEN,
        "modo voz": VoiceCommand.CONTINUOUS,
        "escuta continua": VoiceCommand.CONTINUOUS,
        "ativar escuta continua": VoiceCommand.CONTINUOUS,
        "conversa por voz": VoiceCommand.CONTINUOUS,
        "conversar por voz": VoiceCommand.CONTINUOUS,
        "parar voz": VoiceCommand.STOP,
        "pare de ouvir": VoiceCommand.STOP,
        "parar": VoiceCommand.STOP,
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
        if not capabilities.output_available and not capabilities.input_available:
            return f"Voz indisponível. {capabilities.detail}"
        output = "ligada" if self.auto_speak else "desligada"
        mode = "contínuo" if self.continuous else "comando único"
        return (
            f"Fala: {'disponível' if capabilities.output_available else 'indisponível'}. "
            f"Escuta: {'configurada' if capabilities.input_available else 'indisponível'}. "
            f"Respostas faladas: {output}. Modo: {mode}."
            f" {capabilities.detail}"
        )

    def can_speak_response(self, intent: str) -> bool:
        return self.auto_speak and not intent.startswith("journal.")
