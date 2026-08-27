"""Redação de conteúdo privado antes da persistência operacional."""

from __future__ import annotations

import re
import unicodedata


PRIVATE_JOURNAL_REDACTION = "[conteúdo privado do diário]"


def is_private_journal_text(text: str) -> bool:
    decomposed = unicodedata.normalize("NFKD", str(text or "").casefold())
    normalized = "".join(
        character
        for character in decomposed
        if not unicodedata.combining(character)
    )
    return bool(re.search(r"\bdiario\b", normalized))


__all__ = ["PRIVATE_JOURNAL_REDACTION", "is_private_journal_text"]
