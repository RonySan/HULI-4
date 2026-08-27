"""Parsers determinísticos dos comandos do diário."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
import re
from zoneinfo import ZoneInfo


@dataclass(frozen=True, slots=True)
class JournalDraft:
    content: str
    entry_date: date
    mood: str | None
    tags: tuple[str, ...]
    mood_provided: bool = False
    tags_provided: bool = False


def strip_huli_prefix(text: str) -> str:
    return re.sub(
        r"^\s*huli\s*[,;:]?\s*",
        "",
        str(text or "").strip(),
        flags=re.IGNORECASE,
    ).strip()


def parse_journal_create(
    text: str,
    *,
    timezone_name: str,
    now: datetime | None = None,
) -> JournalDraft:
    raw = strip_huli_prefix(text)
    patterns = (
        re.compile(
            r"^di[aá]rio(?:\s+de\s+(?:hoje|ontem|\d{1,2}/\d{1,2}(?:/\d{2,4})?))?\s*[:\-]\s*(?P<content>.+)$",
            re.IGNORECASE | re.DOTALL,
        ),
        re.compile(
            r"^(?:anote|anota|registre|registra|escreva|escreve|salve|guarde)\s+(?:isso\s+)?(?:(?:no|em)\s+)?(?:meu\s+)?di[aá]rio(?:\s+de\s+(?:hoje|ontem|\d{1,2}/\d{1,2}(?:/\d{2,4})?))?\s*(?::|\-)?\s*(?:que\s+)?(?P<content>.+)$",
            re.IGNORECASE | re.DOTALL,
        ),
    )
    match = next((pattern.match(raw) for pattern in patterns if pattern.match(raw)), None)
    if match is None:
        raise ValueError(
            "Para registrar, use: diário: hoje aconteceu algo importante."
        )
    prefix = raw[: match.start("content")]
    content, mood, tags, mood_provided, tags_provided = _parse_metadata(
        match.group("content")
    )
    return JournalDraft(
        content=content,
        entry_date=_resolve_entry_date(prefix, timezone_name=timezone_name, now=now),
        mood=mood,
        tags=tags,
        mood_provided=mood_provided,
        tags_provided=tags_provided,
    )


def parse_journal_update(
    text: str,
    *,
    timezone_name: str,
    now: datetime | None = None,
) -> tuple[int, JournalDraft]:
    raw = strip_huli_prefix(text)
    match = re.match(
        r"^(?:edite|editar|altere|alterar|corrija|corrigir)\s+(?:a\s+)?(?:entrada|anota[cç][aã]o)?\s*#?(?P<id>\d+)\s+(?:do|no)\s+(?:meu\s+)?di[aá]rio\s*[:\-]\s*(?P<content>.+)$",
        raw,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if match is None:
        raise ValueError(
            "Para editar, use: edite a entrada #1 do diário: novo texto."
        )
    content, mood, tags, mood_provided, tags_provided = _parse_metadata(
        match.group("content")
    )
    return int(match.group("id")), JournalDraft(
        content=content,
        entry_date=_resolve_entry_date("", timezone_name=timezone_name, now=now),
        mood=mood,
        tags=tags,
        mood_provided=mood_provided,
        tags_provided=tags_provided,
    )


def extract_journal_entry_id(text: str) -> int:
    match = re.search(r"#?(\d+)\b", strip_huli_prefix(text))
    if match is None:
        raise ValueError(
            "Informe o número da entrada, por exemplo: apague a entrada #1 do diário."
        )
    return int(match.group(1))


def extract_journal_search_query(text: str) -> str:
    raw = strip_huli_prefix(text).strip(" ?.!")
    patterns = (
        r"^(?:procure|buscar?|busque|pesquise)\s+(?:(?:no|em)\s+)?(?:meu\s+)?di[aá]rio\s+(?:por|sobre)\s+(.+)$",
        r"^o\s+que\s+(?:eu\s+)?escrevi\s+(?:no|em)\s+(?:meu\s+)?di[aá]rio\s+sobre\s+(.+)$",
        r"^(?:encontre|mostre)\s+(?:as\s+)?(?:entradas|anota[cç][oõ]es)\s+(?:do|no)\s+(?:meu\s+)?di[aá]rio\s+sobre\s+(.+)$",
    )
    for pattern in patterns:
        match = re.match(pattern, raw, flags=re.IGNORECASE | re.DOTALL)
        if match:
            query = " ".join(match.group(1).split()).strip(" ?.!")
            if query:
                return query
    raise ValueError(
        "Informe o assunto da busca, por exemplo: procure no meu diário por família."
    )


def parse_journal_query_date(
    text: str,
    *,
    timezone_name: str,
    now: datetime | None = None,
) -> date | None:
    raw = strip_huli_prefix(text)
    lowered = raw.casefold()
    timezone = ZoneInfo(timezone_name)
    reference = (now or datetime.now(timezone)).astimezone(timezone)
    if re.search(r"\bontem\b", lowered):
        return reference.date() - timedelta(days=1)
    if re.search(r"\bhoje\b", lowered):
        return reference.date()
    date_match = re.search(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b", raw)
    if date_match is None:
        return None
    return _date_from_match(date_match, reference)


def _resolve_entry_date(
    prefix: str,
    *,
    timezone_name: str,
    now: datetime | None,
) -> date:
    timezone = ZoneInfo(timezone_name)
    reference = (now or datetime.now(timezone)).astimezone(timezone)
    lowered = prefix.casefold()
    if re.search(r"\bontem\b", lowered):
        return reference.date() - timedelta(days=1)
    date_match = re.search(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b", prefix)
    if date_match:
        return _date_from_match(date_match, reference)
    return reference.date()


def _date_from_match(match: re.Match[str], reference: datetime) -> date:
    day = int(match.group(1))
    month = int(match.group(2))
    raw_year = match.group(3)
    year = reference.year if raw_year is None else int(raw_year)
    if year < 100:
        year += 2000
    try:
        return date(year, month, day)
    except ValueError as exc:
        raise ValueError("A data informada para o diário é inválida.") from exc


def _parse_metadata(
    raw_content: str,
) -> tuple[str, str | None, tuple[str, ...], bool, bool]:
    segments = [segment.strip() for segment in raw_content.split("|")]
    content_parts: list[str] = []
    mood: str | None = None
    tags: tuple[str, ...] = ()
    mood_provided = False
    tags_provided = False

    for segment in segments:
        mood_match = re.match(r"^humor\s*:\s*(.*)$", segment, re.IGNORECASE)
        tags_match = re.match(
            r"^(?:tags|etiquetas)\s*:\s*(.*)$",
            segment,
            re.IGNORECASE,
        )
        if mood_match:
            mood = mood_match.group(1).strip() or None
            mood_provided = True
        elif tags_match:
            tags = tuple(
                value.strip()
                for value in tags_match.group(1).split(",")
                if value.strip()
            )
            tags_provided = True
        elif segment:
            content_parts.append(segment)

    content = " | ".join(content_parts).strip(" .")
    if not content:
        raise ValueError("A entrada do diário não pode estar vazia.")
    return content, mood, tags, mood_provided, tags_provided


__all__ = [
    "JournalDraft",
    "extract_journal_entry_id",
    "extract_journal_search_query",
    "parse_journal_create",
    "parse_journal_query_date",
    "parse_journal_update",
]
