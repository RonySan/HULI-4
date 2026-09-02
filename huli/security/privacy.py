"""Redação de conteúdo privado antes da persistência operacional."""

from __future__ import annotations

import re
import unicodedata

from dataclasses import replace

from huli.core.contracts import KernelRequest, KernelResponse


PRIVATE_JOURNAL_REDACTION = "[conteúdo privado do diário]"
SECRET_REDACTION = "[conteúdo confidencial removido]"

_SECRET_PATTERNS = (
    re.compile(r"\b(?:senha|password|passcode|api[ _-]?key|token|secret|chave privada)\b", re.IGNORECASE),
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)


def contains_secret_text(text: str) -> bool:
    return any(pattern.search(str(text or "")) for pattern in _SECRET_PATTERNS)


def redact_private_text(text: str) -> str:
    if is_private_journal_text(text):
        return PRIVATE_JOURNAL_REDACTION
    if contains_secret_text(text):
        return SECRET_REDACTION
    return text


def filter_private_input(request: KernelRequest) -> tuple[KernelRequest, KernelResponse | None]:
    """Recusa segredos antes dos eventos, Skills, histórico e contexto."""
    if not contains_secret_text(request.text):
        return request, None
    protected = replace(request, text=redact_private_text(request.text))
    return protected, KernelResponse(
        request_id=request.request_id,
        text="A Huli não armazena senhas, tokens ou chaves. Remova esse conteúdo e tente novamente.",
        handled_by="privacy",
        ok=False,
    )


def is_private_journal_text(text: str) -> bool:
    decomposed = unicodedata.normalize("NFKD", str(text or "").casefold())
    normalized = "".join(
        character
        for character in decomposed
        if not unicodedata.combining(character)
    )
    return bool(re.search(r"\bdiario\b", normalized))


__all__ = ["PRIVATE_JOURNAL_REDACTION", "SECRET_REDACTION", "is_private_journal_text", "contains_secret_text", "redact_private_text", "filter_private_input"]
