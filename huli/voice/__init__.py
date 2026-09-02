"""Entrada, síntese e processamento local de voz da Huli."""

from huli.voice.service import (
    VoiceCapabilities,
    VoiceCancelledError,
    VoiceError,
    VoiceService,
    VoiceTimeoutError,
    VoiceUnavailableError,
    WindowsSpeechBackend,
)
from huli.voice.console import HybridInputResult, read_hybrid_input
from huli.voice.calibration import WakeAliasStore, select_repeated_aliases
from huli.voice.session import VoiceCommand, VoiceSession, parse_voice_command
from huli.voice.wake import (
    WakeEvent,
    WakeEventKind,
    WakeWordListener,
    extract_wake_command,
    parse_wake_control,
)

__all__ = [
    "VoiceCapabilities",
    "VoiceCancelledError",
    "VoiceCommand",
    "VoiceError",
    "HybridInputResult",
    "VoiceService",
    "VoiceSession",
    "VoiceTimeoutError",
    "VoiceUnavailableError",
    "WindowsSpeechBackend",
    "WakeEvent",
    "WakeEventKind",
    "WakeWordListener",
    "WakeAliasStore",
    "extract_wake_command",
    "read_hybrid_input",
    "parse_voice_command",
    "parse_wake_control",
    "select_repeated_aliases",
]
