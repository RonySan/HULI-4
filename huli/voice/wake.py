"""Ativação local em segundo plano com prioridade para o teclado."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from queue import Empty, Full, Queue
import re
from threading import Event, Thread
import time

from huli.brain.normalization import normalize_text
from huli.voice.calibration import normalize_wake_alias
from huli.voice.service import (
    VoiceCancelledError,
    VoiceError,
    VoiceService,
    VoiceTimeoutError,
    VoiceUnavailableError,
)
from huli.voice.transcript import canonical_safe_voice_query


# Compatibilidade textual restrita ao nome real. A ativação normal usa o detector
# fonético; palavras comuns nunca são promovidas a aliases da Huli.
_WAKE_PREFIX = re.compile(
    r"^\s*(?:huli|ruli|ruly|ru[\s-]+li)\b[\s,;:!?]*(.*)$",
    re.IGNORECASE | re.DOTALL,
)


class WakeEventKind(StrEnum):
    STATUS = "status"
    COMMAND = "command"
    ERROR = "error"
    HEARD = "heard"


@dataclass(frozen=True, slots=True)
class WakeEvent:
    kind: WakeEventKind
    text: str


def extract_wake_command(
    transcript: str,
    aliases: tuple[str, ...] = (),
) -> str | None:
    """Retorna o comando após o nome; string vazia significa só o chamado."""
    match = _WAKE_PREFIX.fullmatch(str(transcript or ""))
    if match:
        command = match.group(1).strip()
        return canonical_safe_voice_query(command) or command
    normalized = normalize_text(str(transcript or ""))
    custom = sorted(
        {
            alias
            for raw in aliases
            if (alias := normalize_wake_alias(raw)) is not None
        },
        key=len,
        reverse=True,
    )
    for alias in custom:
        if normalized == alias:
            return ""
        prefix = f"{alias} "
        if normalized.startswith(prefix):
            command = normalized[len(prefix):].strip()
            return canonical_safe_voice_query(command) or command
    return None


def parse_wake_control(text: str) -> bool | None:
    """True ativa, False pausa e None indica que não é controle de ativação."""
    normalized = normalize_text(text)
    if normalized in {"ativar huli", "ativar ativacao", "ligar ativacao"}:
        return True
    if normalized in {
        "pausar huli",
        "pausar ativacao",
        "desativar huli",
        "desligar ativacao",
        "privacidade",
    }:
        return False
    return None


class WakeWordListener:
    """Escuta somente a ativação e entrega comandos ao fluxo principal."""

    def __init__(
        self,
        service: VoiceService,
        *,
        cycle_timeout: int = 30,
        command_timeout: int = 20,
        feedback: bool = False,
        aliases: tuple[str, ...] = (),
    ) -> None:
        self.service = service
        self.cycle_timeout = cycle_timeout
        self.command_timeout = command_timeout
        self.feedback = feedback
        self.aliases = tuple(
            alias
            for raw in aliases
            if (alias := normalize_wake_alias(raw)) is not None
        )
        self.events: Queue[WakeEvent] = Queue(maxsize=8)
        self._stop = Event()
        self._paused = Event()
        self._typing = Event()
        self._cancel = Event()
        self._enabled = Event()
        self._idle = Event()
        self._enabled.set()
        self._idle.set()
        self._thread: Thread | None = None
        self._last_feedback = 0.0

    @property
    def enabled(self) -> bool:
        return self._enabled.is_set()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self.service.prepare_input()
        self._stop.clear()
        self._thread = Thread(target=self._run, name="huli-wake-listener", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._cancel.set()
        if self._thread:
            self._thread.join(timeout=2)

    def pause(self) -> None:
        self._paused.set()
        self._cancel.set()
        self._idle.wait(timeout=2)

    def resume(self) -> None:
        self._paused.clear()
        if self.enabled and not self._typing.is_set():
            self._cancel.clear()

    def enable(self) -> None:
        self._enabled.set()

    def disable(self) -> None:
        self._enabled.clear()
        self._cancel.set()

    def set_typing(self, active: bool) -> None:
        if active:
            self._typing.set()
            self._cancel.set()
        else:
            self._typing.clear()
            if self.enabled and not self._paused.is_set():
                self._cancel.clear()

    def set_aliases(self, aliases: tuple[str, ...]) -> None:
        self.aliases = tuple(
            alias
            for raw in aliases
            if (alias := normalize_wake_alias(raw)) is not None
        )

    def get_event(self) -> WakeEvent | None:
        try:
            return self.events.get_nowait()
        except Empty:
            return None

    def _emit(self, kind: WakeEventKind, text: str) -> bool:
        try:
            self.events.put_nowait(WakeEvent(kind, text))
            return True
        except Full:
            if kind is not WakeEventKind.COMMAND:
                return False
            # Um comando tem prioridade sobre uma mensagem visual antiga.
            try:
                self.events.get_nowait()
                self.events.put_nowait(WakeEvent(kind, text))
                return True
            except (Empty, Full):
                return False

    def _ready(self) -> bool:
        return self.enabled and not self._paused.is_set() and not self._typing.is_set()

    def _emit_feedback(self, text: str) -> None:
        if not self.feedback:
            return
        now = time.monotonic()
        if now - self._last_feedback < 2.0:
            return
        self._last_feedback = now
        self._emit(WakeEventKind.HEARD, text)

    def _deliver(self, command: str) -> None:
        if not command or not self._ready():
            return
        self._paused.set()
        self._cancel.set()
        if not self._emit(WakeEventKind.COMMAND, command):
            self.resume()

    def _run(self) -> None:
        while not self._stop.is_set():
            if not self._ready():
                self._stop.wait(0.05)
                continue
            activated = False
            self._idle.clear()
            try:
                transcript = self.service.listen_wake_once(
                    timeout=self.cycle_timeout,
                    cancel_event=self._cancel,
                    aliases=self.aliases,
                )
                if not self._ready():
                    continue
                command = extract_wake_command(transcript, self.aliases)
                if command is None:
                    heard = " ".join(str(transcript or "").split())[:80]
                    if heard:
                        self._emit_feedback(
                            f"Ouvi “{heard}”, mas não reconheci o chamado Huli."
                        )
                    continue
                if command:
                    self._deliver(command)
                    continue
                activated = True
                self._emit(WakeEventKind.STATUS, "Huli: Estou ouvindo...")
                spoken = self.service.listen_once(
                    timeout=self.command_timeout,
                    cancel_event=self._cancel,
                )
                nested = extract_wake_command(spoken, self.aliases)
                self._deliver(nested if nested is not None else spoken)
            except VoiceCancelledError:
                continue
            except VoiceTimeoutError:
                if activated and self._ready():
                    self._emit(
                        WakeEventKind.STATUS,
                        "Huli: Ouvi o chamado, mas não recebi um comando completo.",
                    )
            except VoiceUnavailableError as exc:
                self._emit(WakeEventKind.ERROR, f"Huli: Ativação por voz indisponível: {exc}")
                self._enabled.clear()
            except VoiceError:
                # Ruído ou baixa confiança nunca vira comando nem polui o terminal.
                self._emit_feedback(
                    "Ouvi áudio, mas não entendi o chamado com segurança."
                )
                self._stop.wait(0.2)
            finally:
                self._idle.set()
