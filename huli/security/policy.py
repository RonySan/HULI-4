"""Políticas mínimas de segurança da fundação da Huli."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SecurityPolicy:
    """Limites centrais usados antes de executar ações sensíveis."""

    min_password_length: int = 4
    max_input_chars: int = 10_000
    session_hours: int = 24 * 7
    guest_commands: frozenset[str] = frozenset(
        {"ping", "status", "status huli", "teste", "teste skill"}
    )

    def validate_password(self, password: str) -> None:
        """Aceita senha vazia; se houver senha, aplica um mínimo simples."""
        if not isinstance(password, str):
            raise ValueError("A senha precisa ser texto.")
        if password == "":
            return
        if len(password) < self.min_password_length:
            raise ValueError(
                "A senha é opcional. Se você escolher usar uma, "
                f"ela precisa ter pelo menos {self.min_password_length} caracteres."
            )

    def validate_input(self, text: str) -> None:
        if len(text) > self.max_input_chars:
            raise ValueError(
                f"A mensagem excede o limite de {self.max_input_chars} caracteres."
            )

    def guest_can_execute(self, text: str) -> bool:
        """Permite ao visitante apenas capacidades básicas e não sensíveis."""
        return str(text or "").strip().casefold() in self.guest_commands
