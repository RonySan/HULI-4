"""Normalização determinística usada pelo Knowledge Graph."""

from __future__ import annotations

import re
import unicodedata


def normalize_knowledge_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", str(value or "").casefold())
    without_accents = "".join(
        char for char in decomposed if not unicodedata.combining(char)
    )
    cleaned = re.sub(r"[^a-z0-9]+", " ", without_accents)
    return " ".join(cleaned.split()).strip()
