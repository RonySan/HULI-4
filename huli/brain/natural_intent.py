"""Camada de compatibilidade para frases naturais equivalentes."""

from __future__ import annotations

import re

from huli.brain.intent import IntentEngine as BaseIntentEngine
from huli.brain.intent import IntentMatch, IntentName
from huli.brain.normalization import normalize_text


_AGENDA_QUERY_PATTERNS = (
    re.compile(
        r"^(?:agenda|agendas|minha agenda|minhas agendas|nossa agenda|nossas agendas|"
        r"compromissos|meus compromissos|meus agendamentos|proximos compromissos|"
        r"proximos agendamentos)$"
    ),
    re.compile(
        r"^(?:ver|mostrar|mostra|consultar|consulta)\s+(?:(?:a|minha|nossa)\s+)?agenda$"
    ),
    re.compile(
        r"^o que\s+(?:(?:eu|nos)\s+)?(?:tenho|temos|tem)\s+"
        r"(?:na|minha|na minha|em minha)\s+agenda(?:\s+(?:hoje|amanha))?$"
    ),
    re.compile(
        r"^tem\s+(?:algo|alguma coisa|algum compromisso|algum evento)\s+na\s+agenda"
        r"(?:\s+(?:hoje|amanha))?$"
    ),
    re.compile(
        r"^quais\s+(?:sao\s+)?(?:os\s+)?(?:meus\s+)?(?:compromissos|agendamentos)"
        r"(?:\s+(?:de|para|pra)\s+(?:hoje|amanha))?$"
    ),
)


class NaturalIntentEngine(BaseIntentEngine):
    """Expande frases naturais sem alterar o núcleo determinístico de intenções."""

    def classify(self, text: str) -> IntentMatch:
        normalized = normalize_text(text)
        normalized_without_wake = re.sub(r"^huli\s+", "", normalized).strip()

        for pattern in _AGENDA_QUERY_PATTERNS:
            if pattern.fullmatch(normalized_without_wake):
                return IntentMatch(
                    IntentName.AGENDA_QUERY,
                    0.985,
                    normalized_without_wake,
                    {"matched_rule": "agenda-query-natural"},
                )

        return super().classify(text)


__all__ = ["NaturalIntentEngine"]
