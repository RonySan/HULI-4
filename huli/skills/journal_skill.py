"""Skill privada para registrar, consultar e administrar o diário."""

from __future__ import annotations

from huli.core.contracts import KernelRequest, KernelResponse
from huli.journal import JournalEntry, JournalPolicyError, JournalService
from huli.journal.parsing import (
    extract_journal_entry_id,
    extract_journal_search_query,
    parse_journal_create,
    parse_journal_query_date,
    parse_journal_update,
)
from huli.security import AuthenticationError, AuthService


class JournalSkill:
    name = "journal"
    intents = (
        "journal.create",
        "journal.list",
        "journal.search",
        "journal.update",
        "journal.delete",
        "journal.trash",
        "journal.restore",
        "journal.help",
    )

    def __init__(
        self,
        journal: JournalService,
        timezone_name: str,
        auth: AuthService,
    ) -> None:
        self.journal = journal
        self.timezone_name = timezone_name
        self.auth = auth

    def can_handle(self, request: KernelRequest) -> bool:
        return str(request.metadata.get("intent") or "") in self.intents

    def handle(self, request: KernelRequest) -> KernelResponse:
        if str(request.metadata.get("role") or "guest") != "owner":
            return self._response(
                request,
                "O diário é privado e exige autenticação do proprietário.",
                ok=False,
            )
        owner = " ".join(str(request.metadata.get("username") or "").split()).strip()
        if not owner:
            return self._response(
                request,
                "Não foi possível confirmar o proprietário do diário.",
                ok=False,
            )

        intent = str(request.metadata.get("intent") or "")
        if intent == "journal.help":
            return self._help(request)
        try:
            known_owner = self.auth.find_user(owner)
            password_protected = bool(
                known_owner and self.auth.requires_password(known_owner.username)
            )
        except (AuthenticationError, ValueError):
            password_protected = False
        if not password_protected:
            return self._response(
                request,
                "Para proteger seu diário, configure uma senha para o proprietário "
                "com: python tools/set_local_password.py",
                ok=False,
            )

        try:
            if intent == "journal.create":
                return self._create(request, owner)
            if intent == "journal.list":
                return self._list(request, owner)
            if intent == "journal.search":
                return self._search(request, owner)
            if intent == "journal.update":
                return self._update(request, owner)
            if intent == "journal.delete":
                return self._delete(request, owner)
            if intent == "journal.trash":
                return self._trash(request, owner)
            if intent == "journal.restore":
                return self._restore(request, owner)
        except (JournalPolicyError, LookupError, ValueError) as exc:
            return self._response(request, str(exc), ok=False)

        return self._response(
            request,
            "Não reconheci a operação solicitada para o diário.",
            ok=False,
        )

    def _create(self, request: KernelRequest, owner: str) -> KernelResponse:
        draft = parse_journal_create(
            request.text,
            timezone_name=self.timezone_name,
        )
        entry = self.journal.create(
            owner=owner,
            content=draft.content,
            entry_date=draft.entry_date,
            mood=draft.mood,
            tags=draft.tags,
        )
        extras = self._metadata_summary(entry)
        return self._response(
            request,
            f"Entrada #{entry.id} salva no diário em "
            f"{entry.entry_date.strftime('%d/%m/%Y')}{extras}.",
        )

    def _list(self, request: KernelRequest, owner: str) -> KernelResponse:
        target_date = parse_journal_query_date(
            request.text,
            timezone_name=self.timezone_name,
        )
        if target_date is None:
            entries = self.journal.recent(owner=owner, limit=10)
            title = "Entradas mais recentes do seu diário"
        else:
            entries = self.journal.entries_on(owner=owner, entry_date=target_date)
            title = f"Diário de {target_date.strftime('%d/%m/%Y')}"
        return self._entries_response(request, title, entries)

    def _search(self, request: KernelRequest, owner: str) -> KernelResponse:
        query = extract_journal_search_query(request.text)
        entries = self.journal.search(owner=owner, query=query, limit=20)
        return self._entries_response(
            request,
            f"Resultados do diário para “{query}”",
            entries,
        )

    def _update(self, request: KernelRequest, owner: str) -> KernelResponse:
        entry_id, draft = parse_journal_update(
            request.text,
            timezone_name=self.timezone_name,
        )
        entry = self.journal.update(
            owner=owner,
            entry_id=entry_id,
            content=draft.content,
            mood=draft.mood,
            tags=draft.tags,
            preserve_mood=not draft.mood_provided,
            preserve_tags=not draft.tags_provided,
        )
        return self._response(
            request,
            f"Entrada #{entry.id} do diário atualizada com segurança.",
        )

    def _delete(self, request: KernelRequest, owner: str) -> KernelResponse:
        entry_id = extract_journal_entry_id(request.text)
        entry = self.journal.delete(owner=owner, entry_id=entry_id)
        return self._response(
            request,
            f"Entrada #{entry.id} removida do diário.",
        )

    def _trash(self, request: KernelRequest, owner: str) -> KernelResponse:
        entries = self.journal.trash(owner=owner, limit=20)
        return self._entries_response(request, "Lixeira do diário", entries)

    def _restore(self, request: KernelRequest, owner: str) -> KernelResponse:
        entry_id = extract_journal_entry_id(request.text)
        entry = self.journal.restore(owner=owner, entry_id=entry_id)
        return self._response(
            request,
            f"Entrada #{entry.id} restaurada no diário.",
        )

    def _help(self, request: KernelRequest) -> KernelResponse:
        return self._response(
            request,
            "Seu diário é privado. Exemplos:\n"
            "- diário: hoje foi um dia importante\n"
            "- diário: consegui finalizar um projeto | humor: feliz | tags: trabalho\n"
            "- meu diário de hoje\n"
            "- procure no meu diário por família\n"
            "- edite a entrada #1 do diário: texto corrigido\n"
            "- apague a entrada #1 do diário\n"
            "- lixeira do meu diário\n"
            "- restaure a entrada #1 do diário",
        )

    def _entries_response(
        self,
        request: KernelRequest,
        title: str,
        entries: tuple[JournalEntry, ...],
    ) -> KernelResponse:
        if not entries:
            return self._response(
                request,
                f"{title}: nenhuma entrada encontrada.",
            )
        lines = [f"{title}: {len(entries)} entrada(s)."]
        lines.extend(self._format_entry(entry) for entry in entries)
        return self._response(request, "\n".join(lines))

    @staticmethod
    def _format_entry(entry: JournalEntry) -> str:
        content = " ".join(entry.content.split())
        if len(content) > 500:
            content = f"{content[:497].rstrip()}..."
        extras = JournalSkill._metadata_summary(entry)
        return f"#{entry.id} [{entry.entry_date.strftime('%d/%m/%Y')}] {content}{extras}"

    @staticmethod
    def _metadata_summary(entry: JournalEntry) -> str:
        parts: list[str] = []
        if entry.mood:
            parts.append(f"humor: {entry.mood}")
        if entry.tags:
            parts.append(f"etiquetas: {', '.join(entry.tags)}")
        return f" ({'; '.join(parts)})" if parts else ""

    def _response(
        self,
        request: KernelRequest,
        text: str,
        *,
        ok: bool = True,
    ) -> KernelResponse:
        return KernelResponse(
            request_id=request.request_id,
            text=text,
            handled_by=self.name,
            ok=ok,
        )


__all__ = ["JournalSkill"]
