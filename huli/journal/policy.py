"""Políticas de conteúdo e privacidade do diário pessoal."""

from __future__ import annotations

from dataclasses import dataclass
import re

from huli.journal.models import JournalSensitivity
from huli.memory import MemoryPolicy, MemorySensitivity


class JournalPolicyError(ValueError):
    """Entrada recusada pela política do diário."""


@dataclass(frozen=True, slots=True)
class JournalPolicy:
    max_content_chars: int = 10_000
    max_mood_chars: int = 40
    max_tag_chars: int = 40
    max_tags: int = 10

    def validate_content(self, content: str) -> tuple[str, JournalSensitivity]:
        text = self._clean_content(content)
        sensitivity = MemoryPolicy().classify_sensitivity(text)
        if sensitivity is MemorySensitivity.SECRET:
            raise JournalPolicyError(
                "Por segurança, o diário não armazena senhas, tokens, chaves de API "
                "ou outros segredos. Remova o segredo e tente novamente."
            )
        resolved = (
            JournalSensitivity.SENSITIVE
            if sensitivity is MemorySensitivity.SENSITIVE
            else JournalSensitivity.NORMAL
        )
        return text, resolved

    def clean_mood(self, mood: str | None) -> str | None:
        value = " ".join(str(mood or "").split()).strip(" .,:;-")
        if not value:
            return None
        if len(value) > self.max_mood_chars:
            raise JournalPolicyError(
                f"O humor pode ter no máximo {self.max_mood_chars} caracteres."
            )
        return value.casefold()

    def clean_tags(self, tags: tuple[str, ...] | list[str]) -> tuple[str, ...]:
        cleaned: list[str] = []
        seen: set[str] = set()
        for raw_tag in tags:
            tag = " ".join(str(raw_tag or "").split()).strip(" #.,:;-")
            if not tag:
                continue
            if len(tag) > self.max_tag_chars:
                raise JournalPolicyError(
                    f"Cada etiqueta pode ter no máximo {self.max_tag_chars} caracteres."
                )
            key = tag.casefold()
            if key not in seen:
                seen.add(key)
                cleaned.append(key)
        if len(cleaned) > self.max_tags:
            raise JournalPolicyError(
                f"Cada entrada pode ter no máximo {self.max_tags} etiquetas."
            )
        return tuple(cleaned)

    def _clean_content(self, content: str) -> str:
        raw = str(content or "").replace("\r\n", "\n").replace("\r", "\n")
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in raw.split("\n")]
        while lines and not lines[0]:
            lines.pop(0)
        while lines and not lines[-1]:
            lines.pop()
        text = "\n".join(lines).strip()
        if not text:
            raise JournalPolicyError("A entrada do diário não pode estar vazia.")
        if len(text) > self.max_content_chars:
            raise JournalPolicyError(
                f"A entrada do diário pode ter no máximo {self.max_content_chars} caracteres."
            )
        return text


__all__ = ["JournalPolicy", "JournalPolicyError"]
