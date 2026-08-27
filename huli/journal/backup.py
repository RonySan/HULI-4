"""Backup portátil criptografado e restauração transacional do diário."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import json
from pathlib import Path
import re

from huli.journal.models import JournalEntry, JournalSensitivity
from huli.journal.normalization import build_search_text
from huli.journal.policy import JournalPolicy
from huli.journal.repository import JournalRepository
from huli.security.encrypted_file import (
    EncryptedFileError,
    open_json,
    read_envelope,
    seal_json,
    write_envelope,
)


@dataclass(frozen=True, slots=True)
class JournalRestoreResult:
    restored_entries: int
    safety_backup: Path | None


class JournalBackupService:
    def __init__(
        self,
        repository: JournalRepository,
        policy: JournalPolicy,
        backup_dir: Path,
    ) -> None:
        self.repository = repository
        self.policy = policy
        self.backup_dir = Path(backup_dir)

    def create_backup(
        self,
        *,
        owner: str,
        password: str,
        destination: Path | None = None,
        label: str = "manual",
    ) -> Path:
        entries = self.repository.all_entries(owner)
        payload = {
            "schema": 8,
            "entries": [self._serialize(entry) for entry in entries],
        }
        envelope = seal_json(
            payload,
            password=password,
            owner=owner,
            purpose="journal-portable",
        )
        path = destination or self._default_path(owner, label)
        if Path(path).exists():
            raise FileExistsError(
                "O destino do backup já existe. Escolha outro nome para não sobrescrevê-lo."
            )
        return write_envelope(Path(path), envelope)

    def restore_backup(
        self,
        *,
        owner: str,
        password: str,
        source: Path,
        replace_existing: bool = False,
    ) -> JournalRestoreResult:
        envelope = read_envelope(Path(source))
        purpose = str(envelope.get("purpose") or "")
        if purpose not in {"journal-portable", "journal-plaintext-migration"}:
            raise EncryptedFileError("Este arquivo não é um backup de diário restaurável.")
        payload = open_json(
            envelope,
            password=password,
            expected_owner=owner,
            expected_purpose=purpose,
        )
        entries = self._parse_entries(payload, owner=owner, purpose=purpose)
        existing = self.repository.count_all(owner)
        if existing and not replace_existing:
            raise ValueError(
                "O diário atual não está vazio. A restauração exige confirmação explícita "
                "para substituir as entradas existentes."
            )

        safety_backup = None
        if existing:
            safety_backup = self.create_backup(
                owner=owner,
                password=password,
                label="pre-restore",
            )
        restored = self.repository.replace_all(owner, entries)
        return JournalRestoreResult(
            restored_entries=restored,
            safety_backup=safety_backup,
        )

    @staticmethod
    def _serialize(entry: JournalEntry) -> dict[str, object]:
        return {
            "source_id": entry.id,
            "content": entry.content,
            "entry_date": entry.entry_date.isoformat(),
            "mood": entry.mood,
            "tags": list(entry.tags),
            "sensitivity": entry.sensitivity.value,
            "created_at": entry.created_at.isoformat(),
            "updated_at": entry.updated_at.isoformat(),
            "deleted_at": entry.deleted_at.isoformat() if entry.deleted_at else None,
            "is_active": entry.is_active,
        }

    def _parse_entries(
        self,
        payload: dict[str, object],
        *,
        owner: str,
        purpose: str,
    ) -> tuple[JournalEntry, ...]:
        raw_entries = payload.get("entries")
        if not isinstance(raw_entries, list):
            raise EncryptedFileError("O backup não contém uma lista válida de entradas.")
        parsed: list[JournalEntry] = []
        for position, raw in enumerate(raw_entries, start=1):
            if not isinstance(raw, dict):
                raise EncryptedFileError(f"Entrada {position} inválida no backup.")
            try:
                content, detected_sensitivity = self.policy.validate_content(
                    str(raw["content"])
                )
                mood = self.policy.clean_mood(
                    str(raw["mood"]) if raw.get("mood") is not None else None
                )
                if purpose == "journal-plaintext-migration":
                    raw_tags = json.loads(str(raw.get("tags_json") or "[]"))
                else:
                    raw_tags = raw.get("tags", [])
                if not isinstance(raw_tags, list):
                    raise ValueError("etiquetas inválidas")
                tags = self.policy.clean_tags(tuple(str(tag) for tag in raw_tags))
                stored_sensitivity = JournalSensitivity(
                    str(raw.get("sensitivity") or detected_sensitivity.value)
                )
                sensitivity = (
                    JournalSensitivity.SENSITIVE
                    if JournalSensitivity.SENSITIVE
                    in {stored_sensitivity, detected_sensitivity}
                    else JournalSensitivity.NORMAL
                )
                entry_date = date.fromisoformat(str(raw["entry_date"]))
                created_at = datetime.fromisoformat(str(raw["created_at"]))
                updated_at = datetime.fromisoformat(str(raw["updated_at"]))
                raw_deleted_at = raw.get("deleted_at")
                deleted_at = (
                    datetime.fromisoformat(str(raw_deleted_at))
                    if raw_deleted_at not in (None, "")
                    else None
                )
                raw_is_active = raw.get("is_active", True)
                if raw_is_active not in (True, False, 1, 0):
                    raise ValueError("estado ativo inválido")
                is_active = bool(raw_is_active)
                if is_active:
                    deleted_at = None
                elif deleted_at is None:
                    deleted_at = updated_at
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                raise EncryptedFileError(
                    f"Entrada {position} inválida no backup. Nada foi restaurado."
                ) from exc
            parsed.append(
                JournalEntry(
                    id=position,
                    owner=owner,
                    content=content,
                    search_text=build_search_text(content, mood=mood, tags=tags),
                    entry_date=entry_date,
                    mood=mood,
                    tags=tags,
                    sensitivity=sensitivity,
                    created_at=created_at,
                    updated_at=updated_at,
                    deleted_at=deleted_at,
                    is_active=is_active,
                )
            )
        return tuple(parsed)

    def _default_path(self, owner: str, label: str) -> Path:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        safe_owner = re.sub(r"[^A-Za-z0-9_.-]+", "_", owner).strip("._") or "owner"
        safe_label = re.sub(r"[^A-Za-z0-9_.-]+", "_", label).strip("._") or "backup"
        return self.backup_dir / f"journal-{safe_label}-{safe_owner}-{stamp}.hulibak"


__all__ = ["JournalBackupService", "JournalRestoreResult"]
