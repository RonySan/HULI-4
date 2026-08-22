"""Políticas mínimas de segurança da fundação da Huli."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SecurityPolicy:
    """Limites centrais usados antes de executar ações sensíveis."""

    min_password_length: int = 10
    max_input_chars: int = 10_000
    session_hours: int = 24 * 7

    def validate_password(self, password: str) -> None:
        if not isinstance(password, str):
            raise ValueError("A senha precisa ser texto.")
        if len(password) < self.min_password_length:
            raise ValueError(
                f"A senha precisa ter pelo menos {self.min_password_length} caracteres."
            )

    def validate_input(self, text: str) -> None:
        if len(text) > self.max_input_chars:
            raise ValueError(
                f"A mensagem excede o limite de {self.max_input_chars} caracteres."
            )
