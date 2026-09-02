"""Ajustes conservadores de vocativo, somente para transcrições de voz."""

from __future__ import annotations

import re

from huli.brain.intent import IntentEngine, IntentName
from huli.brain.normalization import normalize_text


_VOCATIVES = frozenset(
    {"huli", "ruli", "ruly", "ru li"}
)
_PREFIX = re.compile(
    r"^(?:huli|ruli|ruly|ru[\s-]+li)[\s,;:!?]+(.+)$",
    re.IGNORECASE | re.DOTALL,
)
_SAFE_MISHEARD_QUERIES = {
    "hoje sao": "que horas são",
    "que hoje": "que dia é hoje",
}
def canonical_safe_voice_query(text: str) -> str | None:
    """Corrige somente erros reais observados que resultam em consulta pública."""
    return _SAFE_MISHEARD_QUERIES.get(normalize_text(text))


def is_spoken_vocative(text: str) -> bool:
    """Um chamado isolado não é um comando nem ativa o microfone."""
    return normalize_text(text) in _VOCATIVES


def normalize_spoken_vocative(text: str) -> str:
    """Corrige vocativo ou erro observado somente em consultas de hora e data.

    Reutiliza a classificação de consultas públicas e mantém intactos todos
    os outros textos, inclusive anotações, negações e comandos sensíveis.
    Não procura palavras parecidas no meio da frase nem usa busca aproximada.
    """
    safe_query = canonical_safe_voice_query(text)
    if safe_query:
        return safe_query
    match = _PREFIX.fullmatch(text.strip())
    if match:
        question = match.group(1).strip()
        safe_query = canonical_safe_voice_query(question)
        if safe_query:
            return safe_query
        intent = IntentEngine().classify(question).intent
        if intent in {IntentName.TIME_QUERY, IntentName.DATE_QUERY}:
            return question
    return text


def resolve_safe_voice_query(text: str) -> str | None:
    """Resolve apenas consultas públicas de hora/data após correções limitadas."""
    corrected = normalize_spoken_vocative(text)
    intent = IntentEngine().classify(corrected).intent
    if intent in {IntentName.TIME_QUERY, IntentName.DATE_QUERY}:
        return corrected
    return None
