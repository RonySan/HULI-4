"""Políticas de segurança e aprendizado da Memory Engine."""

from __future__ import annotations

from dataclasses import dataclass
import re

from huli.memory.models import MemoryKind, MemorySensitivity
from huli.security.privacy import contains_secret_text


_SENSITIVE_PATTERNS = (
    re.compile(r"\b(?:cpf|rg|documento pessoal)\b", re.IGNORECASE),
    re.compile(r"\b(?:cart[aã]o|conta banc[aá]ria|pix)\b", re.IGNORECASE),
    re.compile(r"\b(?:sa[uú]de|doen[cç]a|diagn[oó]stico|medicamento)\b", re.IGNORECASE),
)


class MemoryPolicyError(ValueError):
    """Memória recusada pela política de segurança."""


@dataclass(frozen=True, slots=True)
class MemoryPolicy:
    min_auto_confidence: float = 0.90
    max_content_chars: int = 4000
    auto_kinds: frozenset[MemoryKind] = frozenset(
        {
            MemoryKind.SEMANTIC,
            MemoryKind.PROJECT,
            MemoryKind.PREFERENCE,
            MemoryKind.PERSON,
            MemoryKind.TEMPORAL,
        }
    )

    def classify_sensitivity(self, content: str) -> MemorySensitivity:
        text = str(content or "").strip()
        if contains_secret_text(text):
            return MemorySensitivity.SECRET
        if any(pattern.search(text) for pattern in _SENSITIVE_PATTERNS):
            return MemorySensitivity.SENSITIVE
        return MemorySensitivity.NORMAL

    def validate_content(self, content: str) -> str:
        text = " ".join(str(content or "").split()).strip()
        if not text:
            raise MemoryPolicyError("A memória não pode estar vazia.")
        if len(text) > self.max_content_chars:
            raise MemoryPolicyError(
                f"A memória pode ter no máximo {self.max_content_chars} caracteres."
            )
        return text

    def validate_store(
        self,
        *,
        content: str,
        kind: MemoryKind,
        sensitivity: MemorySensitivity,
        explicit: bool,
        confidence: float,
    ) -> None:
        self.validate_content(content)
        if sensitivity is MemorySensitivity.SECRET:
            raise MemoryPolicyError(
                "A Huli não armazena senhas, tokens, chaves de API ou outros segredos."
            )
        if explicit:
            return
        if sensitivity is MemorySensitivity.SENSITIVE:
            raise MemoryPolicyError(
                "Conteúdo sensível exige memória explícita do proprietário."
            )
        if kind not in self.auto_kinds:
            raise MemoryPolicyError(
                f"Memórias do tipo '{kind.value}' não são aprendidas automaticamente."
            )
        if confidence < self.min_auto_confidence:
            raise MemoryPolicyError(
                "A confiança do aprendizado automático está abaixo do limite permitido."
            )
