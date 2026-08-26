"""Persistência SQLite da Huli."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
import sqlite3

_SCHEMA_VERSION = 4


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

    def schema_version(self) -> int:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT COALESCE(MAX(version), 0) AS version FROM schema_migrations"
            ).fetchone()
            return int(row["version"]) if row else 0

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


__all__ = ["SQLiteDatabase", "_SCHEMA_VERSION"]
