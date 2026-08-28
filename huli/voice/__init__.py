"""Entrada, síntese e processamento local de voz da Huli."""

from huli.voice.service import (
    VoiceCapabilities,
    VoiceError,
    VoiceService,
    VoiceTimeoutError,
    VoiceUnavailableError,
    WindowsSpeechBackend,
)
from huli.voice.session import VoiceCommand, VoiceSession, parse_voice_command

__all__ = [
    "VoiceCapabilities",
    "VoiceCommand",
    "VoiceError",
    "VoiceService",
    "VoiceSession",
    "VoiceTimeoutError",
    "VoiceUnavailableError",
    "WindowsSpeechBackend",
    "parse_voice_command",
]
