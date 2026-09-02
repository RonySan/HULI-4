"""Calibração textual local da palavra de ativação; nenhum áudio é persistido."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Iterable

from huli.brain.normalization import normalize_text


_BLOCKED_ALIASES = frozenset(
    {
        "a",
        "agora",
        "agenda",
        "ajuda",
        "bom dia",
        "boa tarde",
        "boa noite",
        "como",
        "diario",
        "hoje",
        "nao",
        "oi",
        "ola",
        "parar",
        "por favor",
        "que",
        "sim",
        "voz",
    }
)
_ALLOWED_ALIASES = frozenset({"huli", "ruli", "ruly", "ru li"})


def normalize_wake_alias(value: str) -> str | None:
    """Aceita somente formas curtas que possam representar um nome isolado."""
    normalized = normalize_text(str(value or ""))
    words = normalized.split()
    if not 2 <= len(normalized) <= 24:
        return None
    if not 1 <= len(words) <= 2:
        return None
    if normalized in _BLOCKED_ALIASES:
        return None
    if normalized not in _ALLOWED_ALIASES:
        return None
    if not any(character.isalpha() for character in normalized):
        return None
    return normalized


def select_repeated_aliases(
    samples: Iterable[str],
    *,
    minimum_repetitions: int = 2,
    limit: int = 4,
) -> tuple[str, ...]:
    """Seleciona somente formas seguras do próprio nome repetidas na calibração."""
    candidates = tuple(
        candidate
        for sample in samples
        if (candidate := normalize_wake_alias(sample)) is not None
    )
    counts = Counter(candidates)
    selected = sorted(
        (
            (alias, count)
            for alias, count in counts.items()
            if count >= minimum_repetitions
        ),
        key=lambda item: (-item[1], item[0]),
    )
    return tuple(alias for alias, _count in selected[:limit])


class WakeAliasStore:
    """Arquivo pequeno com aliases normalizados; nunca recebe áudio ou frases."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def load(self) -> tuple[str, ...]:
        if not self.path.is_file():
            return ()
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return ()
        raw_aliases = payload.get("aliases", []) if isinstance(payload, dict) else []
        aliases: list[str] = []
        for raw in raw_aliases if isinstance(raw_aliases, list) else []:
            alias = normalize_wake_alias(str(raw))
            if alias and alias not in aliases:
                aliases.append(alias)
        return tuple(aliases[:8])

    def save(self, aliases: Iterable[str]) -> tuple[str, ...]:
        normalized: list[str] = []
        for raw in aliases:
            alias = normalize_wake_alias(raw)
            if alias and alias not in normalized:
                normalized.append(alias)
        selected = tuple(normalized[:8])
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "aliases": list(selected),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        temporary = self.path.with_suffix(f"{self.path.suffix}.tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(temporary, self.path)
        return selected
