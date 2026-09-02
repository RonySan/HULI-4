"""Entrada híbrida do terminal: teclado prioritário e eventos de ativação."""

from __future__ import annotations

from dataclasses import dataclass
import time

from huli.voice.wake import WakeEventKind, WakeWordListener


@dataclass(frozen=True, slots=True)
class HybridInputResult:
    text: str
    from_voice: bool = False


class _WindowsKeys:
    def __init__(self) -> None:
        import msvcrt

        self._module = msvcrt

    def available(self) -> bool:
        return self._module.kbhit()

    def read(self) -> str:
        return self._module.getwch()


def _redraw(prompt: str, characters: list[str], cursor: int, previous: int) -> int:
    text = "".join(characters)
    padding = " " * max(0, previous - len(text))
    print(f"\r{prompt}{text}{padding}", end="", flush=True)
    move_left = len(text) - cursor + len(padding)
    if move_left:
        print("\b" * move_left, end="", flush=True)
    return len(text)


def _clear_line(prompt: str, width: int) -> None:
    print("\r" + " " * (len(prompt) + width) + "\r", end="", flush=True)


def read_hybrid_input(listener: WakeWordListener, *, prompt: str = "Você: ",
                      keys=None, sleeper=time.sleep) -> HybridInputResult | None:
    """Lê uma linha sem bloquear a fila de voz; nenhuma thread executa comandos."""
    keys = keys or _WindowsKeys()
    characters: list[str] = []
    cursor = 0
    drawn = 0
    print(prompt, end="", flush=True)
    while True:
        # O teclado é consultado primeiro para vencer corridas com falsa ativação.
        if keys.available():
            char = keys.read()
            if char in {"\x00", "\xe0"}:
                code = keys.read()
                if code == "K" and cursor > 0:
                    cursor -= 1
                elif code == "M" and cursor < len(characters):
                    cursor += 1
                elif code == "G":
                    cursor = 0
                elif code == "O":
                    cursor = len(characters)
                elif code == "S" and cursor < len(characters):
                    characters.pop(cursor)
                drawn = _redraw(prompt, characters, cursor, drawn)
                listener.set_typing(bool(characters))
                continue
            if char in {"\r", "\n"}:
                print()
                listener.pause()
                listener.set_typing(False)
                return HybridInputResult("".join(characters))
            if char == "\x03":
                print()
                listener.pause()
                listener.set_typing(False)
                raise KeyboardInterrupt
            if char == "\x1a" and not characters:
                print()
                listener.pause()
                return None
            if char == "\b":
                if cursor > 0:
                    cursor -= 1
                    characters.pop(cursor)
            elif char.isprintable():
                characters.insert(cursor, char)
                cursor += 1
            drawn = _redraw(prompt, characters, cursor, drawn)
            listener.set_typing(bool(characters))
            continue

        event = listener.get_event()
        if event is not None:
            if characters:
                # Um comando captado no início da digitação é descartado em silêncio.
                if event.kind is WakeEventKind.COMMAND:
                    listener.resume()
                continue
            _clear_line(prompt, drawn)
            if event.kind is WakeEventKind.COMMAND:
                listener.pause()
                return HybridInputResult(event.text, from_voice=True)
            print(event.text)
            print(prompt, end="", flush=True)
            drawn = 0
            continue
        sleeper(0.03)
