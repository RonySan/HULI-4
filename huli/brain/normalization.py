"""Normalização textual usada pelo cérebro local da Huli."""

from __future__ import annotations

import re
import unicodedata


_WHITESPACE_RE = re.compile(r"\s+")
_NON_WORD_RE = re.compile(r"[^a-z0-9]+")


def normalize_text(text: str) -> str:
    """Normaliza texto sem aplicar regras de intenção ou domínio."""
    if not isinstance(text, str):
        raise TypeError("O texto precisa ser uma string.")

    decomposed = unicodedata.normalize("NFKD", text.casefold())
    without_accents = "".join(char for char in decomposed if not unicodedata.combining(char))
    words_only = _NON_WORD_RE.sub(" ", without_accents)
    return _WHITESPACE_RE.sub(" ", words_only).strip()
