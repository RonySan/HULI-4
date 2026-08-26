"""Pequenos parsers determinísticos usados pelas Skills da Fase 1."""

from __future__ import annotations

from datetime import datetime, timedelta
import re
import unicodedata
from zoneinfo import ZoneInfo


def normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", str(value or "").casefold())
    without_accents = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(without_accents.split())


def strip_huli_prefix(text: str) -> str:
    value = str(text or "").strip()
    return re.sub(r"^\s*huli\s*[,;:]?\s*", "", value, flags=re.IGNORECASE).strip()


def parse_priority(text: str) -> str:
    normalized = normalize(text)
    if "prioridade alta" in normalized or "urgente" in normalized:
        return "alta"
    if "prioridade baixa" in normalized:
        return "baixa"
    return "normal"


def extract_task_title(text: str) -> str:
    value = strip_huli_prefix(text)
    patterns = (
        r"^(?:adiciona|adicionar|adicione|cria|criar|crie|anota|anotar|anote|registre|registrar)\s+(?:uma\s+)?(?:tarefa|lembrete)\s*[:\-]?\s*",
        r"^(?:nova|criar uma|adicionar uma)\s+tarefa\s*[:\-]?\s*",
        r"^(?:precisamos|preciso|tenho que|temos que)\s+",
    )
    for pattern in patterns:
        updated = re.sub(pattern, "", value, flags=re.IGNORECASE)
        if updated != value:
            value = updated.strip()
            break
    value = re.sub(r"\bprioridade\s+(?:alta|normal|baixa)\b", "", value, flags=re.IGNORECASE)
    return " ".join(value.split()).strip(" .,-")


def extract_completion_target(text: str) -> str:
    value = strip_huli_prefix(text)
    value = re.sub(r"^(?:conclui|concluir|conclua|finaliza|finalizar|finalize|marque|marca)\s+", "", value, flags=re.IGNORECASE)
    value = re.sub(r"^(?:a\s+)?tarefa\s*", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\s+como\s+conclu[ií]da\s*$", "", value, flags=re.IGNORECASE)
    return " ".join(value.split()).strip(" #.,")


def extract_cancel_target(text: str) -> str:
    value = strip_huli_prefix(text)
    value = re.sub(r"^(?:cancela|cancelar|cancele|remove|remover|remova)\s+", "", value, flags=re.IGNORECASE)
    value = re.sub(r"^(?:o\s+)?(?:compromisso|evento|agendamento)\s*", "", value, flags=re.IGNORECASE)
    return " ".join(value.split()).strip(" #.,")


def extract_project_name(text: str) -> str | None:
    raw = strip_huli_prefix(text).strip(" ?.!")
    patterns = (
        r"^(?:vamos falar (?:do|sobre o)|estamos no|mude para o|usar o)\s+projeto\s+(.+)$",
        r"^projeto\s+atual\s+(?:e|é)\s+(.+)$",
        r"^defina\s+(?:o\s+)?projeto\s+(.+)$",
        r"^(?:qual (?:(?:e|é)\s+)?o status do|status do|como (?:esta|está) o)\s+projeto\s+(.+)$",
    )
    for pattern in patterns:
        match = re.match(pattern, raw, flags=re.IGNORECASE)
        if match:
            value = " ".join(match.group(1).split()).strip(" ?.! ")
            return value or None
    return None


def parse_appointment_request(text: str, *, timezone_name: str, now: datetime | None = None) -> tuple[str, datetime]:
    timezone = ZoneInfo(timezone_name)
    reference = (now or datetime.now(timezone)).astimezone(timezone)
    raw = strip_huli_prefix(text)
    normalized = normalize(raw)
    time_match = re.search(r"(?:\bas\b|\bàs\b)\s*(\d{1,2})(?::(\d{2}))?\s*(?:h|horas)?\b", raw, re.IGNORECASE)
    if time_match is None:
        time_match = re.search(r"\b(\d{1,2}):(\d{2})\b", raw)
    if time_match is None:
        raise ValueError("Informe o horário do compromisso, por exemplo: amanhã às 15:00.")
    hour = int(time_match.group(1)); minute = int(time_match.group(2) or 0)
    if hour > 23 or minute > 59:
        raise ValueError("O horário informado é inválido.")
    if "amanha" in normalized:
        target_date = (reference + timedelta(days=1)).date()
    elif "hoje" in normalized:
        target_date = reference.date()
    else:
        date_match = re.search(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b", raw)
        day_match = re.search(r"\bdia\s+(\d{1,2})\b", normalized)
        if date_match:
            day = int(date_match.group(1)); month = int(date_match.group(2)); raw_year = date_match.group(3)
            year = reference.year if raw_year is None else int(raw_year)
            if year < 100: year += 2000
            try: target_date = reference.replace(year=year, month=month, day=day).date()
            except ValueError as exc: raise ValueError("A data do compromisso é inválida.") from exc
        elif day_match:
            day = int(day_match.group(1)); year = reference.year; month = reference.month
            for _ in range(13):
                try: candidate = reference.replace(year=year, month=month, day=day).date()
                except ValueError: candidate = None
                if candidate is not None and candidate >= reference.date(): target_date = candidate; break
                month += 1
                if month == 13: month = 1; year += 1
            else: raise ValueError("Não consegui determinar a data do compromisso.")
        else:
            raise ValueError("Informe a data do compromisso, por exemplo: hoje ou amanhã.")
    start_at = datetime(target_date.year, target_date.month, target_date.day, hour, minute, tzinfo=timezone)
    title = raw
    title = re.sub(r"^(?:agenda|agende|marque|marca|cria|criar|adicione|adiciona)\s+(?:um\s+)?(?:compromisso|evento|agendamento)?\s*", "", title, flags=re.IGNORECASE)
    title = re.sub(r"\b(?:hoje|amanh[aã])\b", "", title, flags=re.IGNORECASE)
    title = re.sub(r"\bdia\s+\d{1,2}\b", "", title, flags=re.IGNORECASE)
    title = re.sub(r"\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b", "", title)
    title = re.sub(r"(?:\bas\b|\bàs\b)\s*\d{1,2}(?::\d{2})?\s*(?:h|horas)?\b", "", title, flags=re.IGNORECASE)
    title = re.sub(r"\b\d{1,2}:\d{2}\b", "", title)
    title = " ".join(title.split()).strip(" ,.-:")
    if not title: raise ValueError("Informe o assunto do compromisso.")
    return title, start_at
