"""Testes de segurança do cofre pessoal da alpha.12."""

from __future__ import annotations

from pathlib import Path

import pytest

from huli.bootstrap import build_runtime
from huli.infrastructure import Settings
from huli.journal.normalization import build_search_text
from huli.security import (
    AuthenticationError,
    EncryptedFileError,
    JournalVaultError,
    JournalVaultIntegrityError,
    JournalVaultLockedError,
)
from huli.security.encrypted_file import open_json, read_envelope
from huli.security.os_protection import default_os_key_protector
from huli.security.os_protection import PasswordOnlyProtector

PASSWORD = "senha-segura-123"


def build_unlocked_runtime(tmp_path: Path):
    runtime = build_runtime(
        Settings(
            environment="test",
            log_level="CRITICAL",
            data_dir=tmp_path,
            journal_lock_minutes=1,
        )
    )
    runtime.auth.create_owner("rony", PASSWORD)
    user, token = runtime.auth.authenticate("rony", PASSWORD)
    return runtime, user, token


def test_new_entry_has_no_plaintext_fields_or_search_terms_in_database(
    tmp_path: Path,
) -> None:
    runtime, _user, _token = build_unlocked_runtime(tmp_path)
    phrase = "Conquista confidencial no projeto Huli Safira"
    entry = runtime.journal.create(
        owner="rony",
        content=phrase,
        mood="orgulhoso",
        tags=("trabalho", "vitória"),
    )

    with runtime.database.connect() as connection:
        row = connection.execute(
            "SELECT * FROM journal_entries WHERE id = ?",
            (entry.id,),
        ).fetchone()
        tokens = connection.execute(
            "SELECT token_hash FROM journal_search_tokens WHERE entry_id = ?",
            (entry.id,),
        ).fetchall()

    assert row is not None
    assert row["content"] == ""
    assert row["search_text"] == ""
    assert row["mood"] is None
    assert row["tags_json"] == "[]"
    assert row["crypto_version"] == 1
    assert bytes(row["content_ciphertext"])
    assert phrase.encode("utf-8") not in bytes(row["content_ciphertext"])
    assert tokens
    assert all(len(str(token["token_hash"])) == 64 for token in tokens)
    assert all("safira" not in str(token["token_hash"]) for token in tokens)

    database_artifacts = [runtime.database.path]
    database_artifacts.extend(runtime.database.path.parent.glob("huli.db-*"))
    raw_storage = b"".join(path.read_bytes() for path in database_artifacts if path.exists())
    assert phrase.encode("utf-8") not in raw_storage
    assert "orgulhoso".encode() not in raw_storage
    assert "vitória".encode() not in raw_storage


def test_vault_locks_on_logout_and_reopens_only_after_valid_login(tmp_path: Path) -> None:
    runtime, _user, token = build_unlocked_runtime(tmp_path)
    runtime.journal.create(owner="rony", content="Registro protegido para novo login.")

    runtime.auth.revoke_token(token)

    assert runtime.journal_vault.is_unlocked("rony") is False
    with pytest.raises(JournalVaultLockedError):
        runtime.journal.recent(owner="rony")
    with pytest.raises(AuthenticationError):
        runtime.auth.authenticate("rony", "senha-errada")
    assert runtime.journal_vault.is_unlocked("rony") is False

    runtime.auth.authenticate("rony", PASSWORD)
    assert runtime.journal.recent(owner="rony")[0].content.startswith("Registro protegido")


def test_vault_locks_after_configured_inactivity(tmp_path: Path) -> None:
    runtime = build_runtime(
        Settings(
            environment="test",
            log_level="CRITICAL",
            data_dir=tmp_path,
            journal_lock_minutes=1,
        )
    )
    clock = [100.0]
    runtime.journal_vault._clock = lambda: clock[0]
    runtime.auth.create_owner("rony", PASSWORD)
    runtime.auth.authenticate("rony", PASSWORD)
    runtime.journal.create(owner="rony", content="Entrada antes do bloqueio automático.")

    clock[0] += 61

    with pytest.raises(JournalVaultLockedError, match="inatividade"):
        runtime.journal.recent(owner="rony")
    assert runtime.journal_vault.is_unlocked("rony") is False


def test_tampered_ciphertext_is_refused_without_showing_content(tmp_path: Path) -> None:
    runtime, _user, _token = build_unlocked_runtime(tmp_path)
    entry = runtime.journal.create(
        owner="rony",
        content="Entrada cuja autenticidade será conferida.",
    )
    with runtime.database.connect() as connection:
        row = connection.execute(
            "SELECT content_ciphertext FROM journal_entries WHERE id = ?",
            (entry.id,),
        ).fetchone()
        damaged = bytearray(row["content_ciphertext"])
        damaged[0] ^= 0x01
        connection.execute(
            "UPDATE journal_entries SET content_ciphertext = ? WHERE id = ?",
            (bytes(damaged), entry.id),
        )

    with pytest.raises(JournalVaultIntegrityError, match="alterado/corrompido"):
        runtime.journal_repository.get(entry.id, "rony")


def test_alpha11_plaintext_is_backed_up_then_migrated_atomically(tmp_path: Path) -> None:
    runtime = build_runtime(
        Settings(environment="test", log_level="CRITICAL", data_dir=tmp_path)
    )
    runtime.auth.create_owner("rony", PASSWORD)
    phrase = "Relato legado muito pessoal da alpha onze"
    with runtime.database.connect() as connection:
        connection.execute(
            """
            INSERT INTO journal_entries(
                owner, content, search_text, entry_date, mood, tags_json,
                sensitivity, created_at, updated_at, is_active
            ) VALUES (?, ?, ?, '2026-08-27', 'reflexivo', '["legado"]',
                      'normal', '2026-08-27T10:00:00+00:00',
                      '2026-08-27T10:00:00+00:00', 1)
            """,
            (
                "rony",
                phrase,
                build_search_text(phrase, mood="reflexivo", tags=("legado",)),
            ),
        )

    runtime.auth.authenticate("rony", PASSWORD)

    with runtime.database.connect() as connection:
        row = connection.execute("SELECT * FROM journal_entries").fetchone()
        vault_row = connection.execute(
            "SELECT legacy_scrub_required, legacy_scrubbed_at FROM journal_vaults"
        ).fetchone()
    assert row["content"] == ""
    assert row["search_text"] == ""
    assert row["crypto_version"] == 1
    assert vault_row["legacy_scrub_required"] == 0
    assert vault_row["legacy_scrubbed_at"]
    assert runtime.journal.recent(owner="rony")[0].content == phrase

    database_artifacts = [runtime.database.path]
    database_artifacts.extend(runtime.database.path.parent.glob("huli.db-*"))
    raw_storage = b"".join(path.read_bytes() for path in database_artifacts if path.exists())
    assert phrase.encode("utf-8") not in raw_storage

    backups = tuple((tmp_path / "backups").glob("journal-pre-alpha12-*.hulibak"))
    assert len(backups) == 1
    assert phrase.encode("utf-8") not in backups[0].read_bytes()
    recovered = open_json(
        read_envelope(backups[0]),
        password=PASSWORD,
        expected_owner="rony",
        expected_purpose="journal-plaintext-migration",
    )
    assert recovered["entries"][0]["content"] == phrase


def test_password_change_rewraps_key_revokes_sessions_and_preserves_diary(
    tmp_path: Path,
) -> None:
    runtime, _user, old_token = build_unlocked_runtime(tmp_path)
    runtime.journal.create(owner="rony", content="Entrada preservada durante a atualização.")

    runtime.auth.set_password(
        "rony",
        "senha-nova-456",
        current_password=PASSWORD,
    )

    with pytest.raises(AuthenticationError):
        runtime.auth.validate_token(old_token)
    with pytest.raises(AuthenticationError):
        runtime.auth.authenticate("rony", PASSWORD)
    runtime.auth.authenticate("rony", "senha-nova-456")
    assert "preservada" in runtime.journal.recent(owner="rony")[0].content

    with pytest.raises(JournalVaultError, match="não pode ser removida"):
        runtime.auth.set_password(
            "rony",
            "",
            current_password="senha-nova-456",
        )


def test_portable_backup_round_trip_and_wrong_password_protection(tmp_path: Path) -> None:
    runtime, _user, _token = build_unlocked_runtime(tmp_path)
    first = runtime.journal.create(owner="rony", content="Primeira entrada do backup.")
    second = runtime.journal.create(owner="rony", content="Segunda entrada na lixeira.")
    runtime.journal.delete(owner="rony", entry_id=second.id)
    backup = runtime.journal_backups.create_backup(owner="rony", password=PASSWORD)

    assert "Primeira entrada".encode() not in backup.read_bytes()
    runtime.journal.update(
        owner="rony",
        entry_id=first.id,
        content="Conteúdo que será substituído pela restauração.",
    )
    with pytest.raises(EncryptedFileError, match="Senha incorreta"):
        runtime.journal_backups.restore_backup(
            owner="rony",
            password="senha-errada",
            source=backup,
            replace_existing=True,
        )
    assert "substituído" in runtime.journal.recent(owner="rony")[0].content

    restored = runtime.journal_backups.restore_backup(
        owner="rony",
        password=PASSWORD,
        source=backup,
        replace_existing=True,
    )

    assert restored.restored_entries == 2
    assert restored.safety_backup is not None
    assert runtime.journal.recent(owner="rony")[0].content == "Primeira entrada do backup."
    assert runtime.journal.trash(owner="rony")[0].content == "Segunda entrada na lixeira."


def test_os_key_protector_round_trip() -> None:
    protector = default_os_key_protector()
    secret = b"envelope-ja-cifrado-pela-senha"

    protected = protector.protect(secret)

    assert protector.unprotect(protected) == secret
    if protector.name.startswith("windows-dpapi"):
        assert protected != secret


def test_password_only_vault_can_upgrade_to_available_os_protection(
    tmp_path: Path,
) -> None:
    class PrefixProtector:
        name = "test-os-protection"

        @staticmethod
        def protect(data: bytes) -> bytes:
            return b"protected:" + data

        @staticmethod
        def unprotect(data: bytes) -> bytes:
            if not data.startswith(b"protected:"):
                raise ValueError("envelope inválido")
            return data.removeprefix(b"protected:")

    runtime = build_runtime(
        Settings(environment="test", log_level="CRITICAL", data_dir=tmp_path)
    )
    runtime.journal_vault.protector = PasswordOnlyProtector()
    runtime.auth.create_owner("rony", PASSWORD)
    _user, token = runtime.auth.authenticate("rony", PASSWORD)
    runtime.journal.create(owner="rony", content="Entrada portátil protegida.")
    runtime.auth.revoke_token(token)

    runtime.journal_vault.protector = PrefixProtector()
    _user, token = runtime.auth.authenticate("rony", PASSWORD)
    runtime.auth.revoke_token(token)
    runtime.auth.authenticate("rony", PASSWORD)

    with runtime.database.connect() as connection:
        row = connection.execute("SELECT os_protection FROM journal_vaults").fetchone()
    assert row["os_protection"] == "test-os-protection"
    assert runtime.journal.recent(owner="rony")[0].content == "Entrada portátil protegida."


def test_old_backup_uses_its_creation_password_after_account_password_change(
    tmp_path: Path,
) -> None:
    runtime, _user, _token = build_unlocked_runtime(tmp_path)
    entry = runtime.journal.create(owner="rony", content="Conteúdo do backup antigo.")
    backup = runtime.journal_backups.create_backup(owner="rony", password=PASSWORD)

    runtime.auth.set_password(
        "rony",
        "senha-nova-456",
        current_password=PASSWORD,
    )
    runtime.auth.authenticate("rony", "senha-nova-456")
    runtime.journal.update(
        owner="rony",
        entry_id=entry.id,
        content="Conteúdo atual antes da recuperação.",
    )

    result = runtime.journal_backups.restore_backup(
        owner="rony",
        password=PASSWORD,
        source=backup,
        replace_existing=True,
    )

    assert result.restored_entries == 1
    assert runtime.journal.recent(owner="rony")[0].content == "Conteúdo do backup antigo."
