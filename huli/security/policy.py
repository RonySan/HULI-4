"""Políticas mínimas de segurança da Huli."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SecurityPolicy:
    min_password_length: int = 4
    max_input_chars: int = 10_000
    session_hours: int = 24 * 7
    guest_commands: frozenset[str] = frozenset(
        {"ping", "status", "status huli", "teste", "teste skill"}
    )
    guest_intents: frozenset[str] = frozenset(
        {
            "smalltalk",
            "time.query",
            "system.status",
            "conversation.mode.set",
            "conversation.mode.query",
        }
    )

    def validate_password(self, password: str) -> None:
        if not isinstance(password, str):
            raise ValueError("A senha precisa ser texto.")
        if password == "":
            return
        if len(password) < self.min_password_length:
            raise ValueError(
                "A senha é opcional. Se você escolher usar uma, ela precisa ter "
                f"pelo menos {self.min_password_length} caracteres."
            )

    def validate_input(self, text: str) -> None:
        if len(text) > self.max_input_chars:
            raise ValueError(
                f"A mensagem excede o limite de {self.max_input_chars} caracteres."
            )

    def guest_can_execute(self, text: str, intent: str | None = None) -> bool:
        command = str(text or "").strip().casefold()
        if command in self.guest_commands:
            return True
        return str(intent or "") in self.guest_intents
