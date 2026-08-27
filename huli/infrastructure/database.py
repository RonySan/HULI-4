"""Persistência SQLite da Huli."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
import sqlite3

_SCHEMA_VERSION = 8


class SQLiteDatabase:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            applied = {
                int(row["version"])
                for row in connection.execute("SELECT version FROM schema_migrations")
            }
            if 1 not in applied:
                self._migration_001_runtime(connection)
                connection.execute("INSERT INTO schema_migrations(version) VALUES (1)")
            if 2 not in applied:
                self._migration_002_auth(connection)
                connection.execute("INSERT INTO schema_migrations(version) VALUES (2)")
            if 3 not in applied:
                self._migration_003_planner(connection)
                connection.execute("INSERT INTO schema_migrations(version) VALUES (3)")
            if 4 not in applied:
                self._migration_004_agenda(connection)
                connection.execute("INSERT INTO schema_migrations(version) VALUES (4)")
            if 5 not in applied:
                self._migration_005_memory(connection)
                connection.execute("INSERT INTO schema_migrations(version) VALUES (5)")
            if 6 not in applied:
                self._migration_006_knowledge(connection)
                connection.execute("INSERT INTO schema_migrations(version) VALUES (6)")
            if 7 not in applied:
                self._migration_007_journal(connection)
                connection.execute("INSERT INTO schema_migrations(version) VALUES (7)")
            if 8 not in applied:
                self._migration_008_journal_vault(connection)
                connection.execute("INSERT INTO schema_migrations(version) VALUES (8)")

    def schema_version(self) -> int:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT COALESCE(MAX(version), 0) AS version FROM schema_migrations"
            ).fetchone()
            return int(row["version"]) if row else 0

    def secure_compact(self) -> None:
        """Reescreve o SQLite e trunca o WAL após remoção de texto legado."""

        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, isolation_level=None)
        try:
            connection.execute("PRAGMA secure_delete = ON")
            connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            connection.execute("VACUUM")
            connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        finally:
            connection.close()

    @staticmethod
    def _migration_001_runtime(connection: sqlite3.Connection) -> None:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_events_name_created_at
            ON events(name, created_at);

            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id TEXT NOT NULL UNIQUE,
                user_text TEXT NOT NULL,
                response_text TEXT NOT NULL,
                handled_by TEXT NOT NULL,
                ok INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_interactions_created_at
            ON interactions(created_at);
            """
        )

    @staticmethod
    def _migration_002_auth(connection: sqlite3.Connection) -> None:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                password_salt TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token_hash TEXT NOT NULL UNIQUE,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                revoked_at TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_sessions_user_expires
            ON sessions(user_id, expires_at);
            """
        )

    @staticmethod
    def _migration_003_planner(connection: sqlite3.Connection) -> None:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                priority TEXT NOT NULL DEFAULT 'normal',
                project TEXT,
                due_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_tasks_status_project
            ON tasks(status, project, id);
            """
        )

    @staticmethod
    def _migration_004_agenda(connection: sqlite3.Connection) -> None:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                start_at TEXT NOT NULL,
                end_at TEXT,
                status TEXT NOT NULL DEFAULT 'scheduled',
                project TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                cancelled_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_appointments_status_start
            ON appointments(status, start_at);
            """
        )

    @staticmethod
    def _migration_005_memory(connection: sqlite3.Connection) -> None:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner TEXT NOT NULL COLLATE NOCASE,
                kind TEXT NOT NULL,
                content TEXT NOT NULL,
                normalized_content TEXT NOT NULL,
                subject TEXT,
                project TEXT,
                sensitivity TEXT NOT NULL,
                source TEXT NOT NULL,
                confidence REAL NOT NULL,
                occurred_at TEXT,
                valid_until TEXT,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_accessed_at TEXT,
                access_count INTEGER NOT NULL DEFAULT 0,
                is_active INTEGER NOT NULL DEFAULT 1
            );

            CREATE INDEX IF NOT EXISTS idx_memories_owner_active_kind
            ON memories(owner, is_active, kind, updated_at);

            CREATE INDEX IF NOT EXISTS idx_memories_owner_project_active
            ON memories(owner, project, is_active, updated_at);

            CREATE INDEX IF NOT EXISTS idx_memories_owner_content
            ON memories(owner, normalized_content, is_active);
            """
        )

    @staticmethod
    def _migration_006_knowledge(connection: sqlite3.Connection) -> None:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS knowledge_entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner TEXT NOT NULL COLLATE NOCASE,
                name TEXT NOT NULL,
                normalized_name TEXT NOT NULL,
                kind TEXT NOT NULL,
                sensitivity TEXT NOT NULL DEFAULT 'normal',
                manual_source INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1
            );
            CREATE UNIQUE INDEX IF NOT EXISTS uq_knowledge_entity
            ON knowledge_entities(owner, normalized_name, kind);
            CREATE INDEX IF NOT EXISTS idx_knowledge_entities_owner_active
            ON knowledge_entities(owner, is_active, kind, normalized_name);

            CREATE TABLE IF NOT EXISTS knowledge_entity_sources (
                entity_id INTEGER NOT NULL,
                memory_id INTEGER NOT NULL,
                PRIMARY KEY(entity_id, memory_id),
                FOREIGN KEY(entity_id) REFERENCES knowledge_entities(id) ON DELETE CASCADE,
                FOREIGN KEY(memory_id) REFERENCES memories(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS knowledge_aliases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner TEXT NOT NULL COLLATE NOCASE,
                entity_id INTEGER NOT NULL,
                alias TEXT NOT NULL,
                normalized_alias TEXT NOT NULL,
                source_memory_id INTEGER,
                is_active INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY(entity_id) REFERENCES knowledge_entities(id) ON DELETE CASCADE,
                FOREIGN KEY(source_memory_id) REFERENCES memories(id) ON DELETE SET NULL
            );
            CREATE UNIQUE INDEX IF NOT EXISTS uq_knowledge_alias
            ON knowledge_aliases(owner, entity_id, normalized_alias);
            CREATE INDEX IF NOT EXISTS idx_knowledge_alias_lookup
            ON knowledge_aliases(owner, normalized_alias, is_active);

            CREATE TABLE IF NOT EXISTS knowledge_relations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner TEXT NOT NULL COLLATE NOCASE,
                subject_id INTEGER NOT NULL,
                predicate TEXT NOT NULL,
                object_id INTEGER NOT NULL,
                sensitivity TEXT NOT NULL DEFAULT 'normal',
                confidence REAL NOT NULL DEFAULT 1.0,
                source_memory_id INTEGER,
                valid_from TEXT,
                valid_until TEXT,
                created_at TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY(subject_id) REFERENCES knowledge_entities(id) ON DELETE CASCADE,
                FOREIGN KEY(object_id) REFERENCES knowledge_entities(id) ON DELETE CASCADE,
                FOREIGN KEY(source_memory_id) REFERENCES memories(id) ON DELETE SET NULL
            );
            CREATE INDEX IF NOT EXISTS idx_knowledge_relations_subject
            ON knowledge_relations(owner, subject_id, predicate, is_active);
            CREATE INDEX IF NOT EXISTS idx_knowledge_relations_object
            ON knowledge_relations(owner, object_id, predicate, is_active);

            CREATE TABLE IF NOT EXISTS knowledge_facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner TEXT NOT NULL COLLATE NOCASE,
                entity_id INTEGER NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                normalized_value TEXT NOT NULL,
                sensitivity TEXT NOT NULL DEFAULT 'normal',
                confidence REAL NOT NULL DEFAULT 1.0,
                source_memory_id INTEGER,
                valid_from TEXT,
                valid_until TEXT,
                created_at TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY(entity_id) REFERENCES knowledge_entities(id) ON DELETE CASCADE,
                FOREIGN KEY(source_memory_id) REFERENCES memories(id) ON DELETE SET NULL
            );
            CREATE INDEX IF NOT EXISTS idx_knowledge_facts_entity
            ON knowledge_facts(owner, entity_id, key, is_active);
            """
        )

    @staticmethod
    def _migration_007_journal(connection: sqlite3.Connection) -> None:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS journal_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner TEXT NOT NULL COLLATE NOCASE,
                content TEXT NOT NULL,
                search_text TEXT NOT NULL,
                entry_date TEXT NOT NULL,
                mood TEXT,
                tags_json TEXT NOT NULL DEFAULT '[]',
                sensitivity TEXT NOT NULL DEFAULT 'normal',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                deleted_at TEXT,
                is_active INTEGER NOT NULL DEFAULT 1
            );

            CREATE INDEX IF NOT EXISTS idx_journal_owner_date_active
            ON journal_entries(owner, entry_date, is_active, created_at);

            CREATE INDEX IF NOT EXISTS idx_journal_owner_search_active
            ON journal_entries(owner, search_text, is_active);
            """
        )

    @staticmethod
    def _migration_008_journal_vault(connection: sqlite3.Connection) -> None:
        """Adiciona envelopes cifrados sem destruir registros da alpha.11.

        A migração estrutural não possui a senha do proprietário. As linhas
        legadas permanecem marcadas com ``crypto_version = 0`` e são cifradas
        atomicamente no primeiro login autenticado, após backup portátil.
        """

        connection.executescript(
            """
            ALTER TABLE journal_entries ADD COLUMN crypto_id TEXT;
            ALTER TABLE journal_entries ADD COLUMN content_nonce BLOB;
            ALTER TABLE journal_entries ADD COLUMN content_ciphertext BLOB;
            ALTER TABLE journal_entries ADD COLUMN search_nonce BLOB;
            ALTER TABLE journal_entries ADD COLUMN search_ciphertext BLOB;
            ALTER TABLE journal_entries ADD COLUMN mood_nonce BLOB;
            ALTER TABLE journal_entries ADD COLUMN mood_ciphertext BLOB;
            ALTER TABLE journal_entries ADD COLUMN tags_nonce BLOB;
            ALTER TABLE journal_entries ADD COLUMN tags_ciphertext BLOB;
            ALTER TABLE journal_entries
                ADD COLUMN crypto_version INTEGER NOT NULL DEFAULT 0;

            CREATE UNIQUE INDEX IF NOT EXISTS uq_journal_crypto_id
            ON journal_entries(crypto_id)
            WHERE crypto_id IS NOT NULL;

            CREATE TABLE IF NOT EXISTS journal_search_tokens (
                entry_id INTEGER NOT NULL,
                token_hash TEXT NOT NULL,
                PRIMARY KEY(entry_id, token_hash),
                FOREIGN KEY(entry_id) REFERENCES journal_entries(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_journal_search_token
            ON journal_search_tokens(token_hash, entry_id);

            CREATE TABLE IF NOT EXISTS journal_vaults (
                user_id INTEGER PRIMARY KEY,
                kdf_salt BLOB NOT NULL,
                kdf_n INTEGER NOT NULL,
                kdf_r INTEGER NOT NULL,
                kdf_p INTEGER NOT NULL,
                wrapped_nonce BLOB NOT NULL,
                wrapped_key BLOB NOT NULL,
                os_protection TEXT NOT NULL,
                crypto_version INTEGER NOT NULL,
                legacy_scrub_required INTEGER NOT NULL DEFAULT 0,
                legacy_scrubbed_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        )


__all__ = ["SQLiteDatabase", "_SCHEMA_VERSION"]
