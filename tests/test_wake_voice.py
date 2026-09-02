"""Ativação por voz testada sem abrir microfone nem executar comandos reais."""

from collections import deque
import time

import pytest

from huli.voice import VoiceCancelledError, VoiceTimeoutError
from huli.voice.console import HybridInputResult, read_hybrid_input
from huli.voice.wake import (
    WakeEvent,
    WakeEventKind,
    WakeWordListener,
    extract_wake_command,
    parse_wake_control,
)


class FakeService:
    def __init__(self, wake=(), commands=()):
        self.wake = deque(wake)
        self.commands = deque(commands)
        self.prepared = False
        self.wake_calls = 0
        self.command_calls = 0

    def prepare_input(self):
        self.prepared = True

    @staticmethod
    def _next_or_cancel(items, cancel_event):
        if items:
            item = items.popleft()
            if isinstance(item, BaseException):
                raise item
            return item
        while not cancel_event.is_set():
            time.sleep(0.005)
        raise VoiceCancelledError("cancelado no teste")

    def listen_wake_once(self, *, timeout, cancel_event, aliases=()):
        self.wake_calls += 1
        self.aliases = tuple(aliases)
        return self._next_or_cancel(self.wake, cancel_event)

    def listen_once(self, *, timeout, cancel_event):
        self.command_calls += 1
        return self._next_or_cancel(self.commands, cancel_event)


@pytest.mark.parametrize(("text", "expected"), [
    ("Huli", ""),
    ("Ruli", ""),
    ("Ru-li", ""),
    ("Ru li, que horas são?", "que horas são?"),
    ("Huli, que horas são?", "que horas são?"),
    ("Huli, hoje são", "que horas são"),
    ("Uli", None),
    ("Juli, que horas são?", None),
    ("único que horas são?", None),
    ("olhe", None),
    ("olhe como está a agenda", None),
    ("hoje são", None),
    ("hoje são três pessoas", None),
    ("não chame a Huli", None),
    ("olheiro", None),
    ("alguém disse olhe", None),
])
def test_wake_prefix_is_narrow_and_preserves_command(text, expected):
    assert extract_wake_command(text) == expected


@pytest.mark.parametrize(("text", "expected"), [
    ("ativar Huli", True),
    ("ligar ativação", True),
    ("pausar ativação", False),
    ("privacidade", False),
    ("ativar voz", None),
])
def test_wake_controls_do_not_replace_existing_voice_controls(text, expected):
    assert parse_wake_control(text) is expected


def test_command_in_same_phrase_is_queued_but_never_executed_in_worker():
    service = FakeService(wake=["huli que horas são"])
    listener = WakeWordListener(service, cycle_timeout=2, command_timeout=8)
    listener.start()
    try:
        event = listener.events.get(timeout=1)
        assert event == WakeEvent(WakeEventKind.COMMAND, "que horas são")
        assert service.prepared
        assert service.command_calls == 0
    finally:
        listener.stop()


def test_calibrated_alias_reaches_listener_but_only_as_wake_prefix():
    service = FakeService(wake=["ruly que horas são"])
    listener = WakeWordListener(
        service,
        cycle_timeout=2,
        command_timeout=8,
        aliases=("ruly",),
    )
    listener.start()
    try:
        event = listener.events.get(timeout=1)
        assert event == WakeEvent(WakeEventKind.COMMAND, "que horas são")
        assert service.aliases == ("ruly",)
        assert service.command_calls == 0
    finally:
        listener.stop()


def test_name_then_pause_requests_and_queues_the_following_phrase():
    service = FakeService(wake=["huli"], commands=["que horas são"])
    listener = WakeWordListener(service, cycle_timeout=2, command_timeout=8)
    listener.start()
    try:
        assert listener.events.get(timeout=1).kind is WakeEventKind.STATUS
        assert listener.events.get(timeout=1) == WakeEvent(
            WakeEventKind.COMMAND,
            "que horas são",
        )
        assert service.command_calls == 1
    finally:
        listener.stop()


def test_typing_prevents_background_recognition_until_keyboard_is_released():
    service = FakeService(wake=["huli que horas são"])
    listener = WakeWordListener(service, cycle_timeout=2, command_timeout=8)
    listener.set_typing(True)
    listener.start()
    try:
        time.sleep(0.05)
        assert service.wake_calls == 0
        listener.set_typing(False)
        assert listener.events.get(timeout=1).kind is WakeEventKind.COMMAND
    finally:
        listener.stop()


def test_normal_wake_cycle_timeout_is_silent():
    service = FakeService(wake=[VoiceTimeoutError("silêncio")])
    listener = WakeWordListener(service, cycle_timeout=2, command_timeout=8)
    listener.start()
    try:
        time.sleep(0.05)
        assert listener.events.empty()
    finally:
        listener.stop()


def test_panel_feedback_shows_unmatched_transcription_without_executing_it():
    service = FakeService(wake=["barulho reconhecido"])
    listener = WakeWordListener(
        service,
        cycle_timeout=2,
        command_timeout=8,
        feedback=True,
    )
    listener.start()
    try:
        event = listener.events.get(timeout=1)
        assert event.kind is WakeEventKind.HEARD
        assert "barulho reconhecido" in event.text
        assert service.command_calls == 0
    finally:
        listener.stop()


def test_pause_cancels_the_current_cycle_and_waits_for_microphone_release():
    service = FakeService()
    listener = WakeWordListener(service, cycle_timeout=2, command_timeout=8)
    listener.start()
    try:
        deadline = time.monotonic() + 1
        while service.wake_calls == 0 and time.monotonic() < deadline:
            time.sleep(0.005)
        listener.pause()
        assert listener._idle.is_set()
    finally:
        listener.stop()


class FakeKeys:
    def __init__(self, characters):
        self.characters = deque(characters)

    def available(self):
        return bool(self.characters)

    def read(self):
        return self.characters.popleft()


class FakeListener:
    def __init__(self, events=()):
        self.events = deque(events)
        self.typing = []
        self.paused = 0
        self.resumed = 0

    def get_event(self):
        return self.events.popleft() if self.events else None

    def set_typing(self, active):
        self.typing.append(active)

    def pause(self):
        self.paused += 1

    def resume(self):
        self.resumed += 1


def test_hybrid_console_supports_insertion_and_keeps_keyboard_priority(capsys):
    listener = FakeListener([WakeEvent(WakeEventKind.COMMAND, "não executar")])
    keys = FakeKeys(["a", "b", "c", "\xe0", "K", "\xe0", "K", "X", "\r"])
    result = read_hybrid_input(listener, keys=keys, sleeper=lambda _: None)
    assert result == HybridInputResult("aXbc")
    assert listener.events
    assert listener.paused == 1
    assert listener.typing[-1] is False
    capsys.readouterr()


def test_hybrid_console_returns_voice_command_without_touching_keyboard(capsys):
    listener = FakeListener([WakeEvent(WakeEventKind.COMMAND, "que horas são")])
    result = read_hybrid_input(listener, keys=FakeKeys([]), sleeper=lambda _: None)
    assert result == HybridInputResult("que horas são", from_voice=True)
    assert listener.paused == 1
    capsys.readouterr()
