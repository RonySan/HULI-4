"""Normalização segura para busca no diário."""

from __future__ import annotations

import re
import unicodedata


def normalize_journal_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", str(value or "").casefold())
    without_accents = "".join(
        character
        for character in decomposed
        if not unicodedata.combining(character)
    )
    cleaned = re.sub(r"[^a-z0-9]+", " ", without_accents)
    return " ".join(cleaned.split()).strip()


def build_search_text(
    content: str,
    *,
    mood: str | None = None,
    tags: tuple[str, ...] = (),
) -> str:
    return normalize_journal_text(" ".join((content, mood or "", *tags)))


__all__ = ["build_search_text", "normalize_journal_text"]
