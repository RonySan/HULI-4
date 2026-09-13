"""Regressões da sincronização local do Google Calendar."""

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from huli.core import EventBus
from huli.infrastructure import AppointmentRepository, Settings, SQLiteDatabase
from huli.integrations.google_calendar import GoogleCalendarService, GoogleTokenStore


class FakeProtector:
    name = "windows-dpapi-current-user"

    def protect(self, data: bytes) -> bytes:
        return b"dpapi:" + data[::-1]

    def unprotect(self, data: bytes) -> bytes:
        assert data.startswith(b"dpapi:")
        return data[len(b"dpapi:") :][::-1]


def test_google_token_store_does_not_write_token_as_plaintext(tmp_path: Path) -> None:
    path = tmp_path / "secrets" / "google_token.json"
    store = GoogleTokenStore(path, FakeProtector())
    payload = {"token": "token-secreto", "refresh_token": "refresh-secreto"}

    store.save(payload)

    assert "token-secreto" not in path.read_text(encoding="utf-8")
    assert store.load() == payload


def test_external_google_events_are_upserted_and_cannot_be_completed_locally(
    tmp_path: Path,
) -> None:
    database = SQLiteDatabase(tmp_path / "huli.db")
    database.initialize()
    repository = AppointmentRepository(database)
    timezone = ZoneInfo("America/Sao_Paulo")
    start = datetime(2026, 9, 10, 9, 0, tzinfo=timezone)

    assert repository.upsert_external(
        source="google",
        external_id="abc123",
        title="Reunião de trabalho",
        start_at=start,
        end_at=None,
        calendar_name="Google Calendar",
    ) == "created"
    assert repository.upsert_external(
        source="google",
        external_id="abc123",
        title="Reunião de trabalho atualizada",
        start_at=start,
        end_at=None,
        calendar_name="Google Calendar",
    ) == "updated"

    item = repository.list_between(start.replace(hour=0), start.replace(hour=23))[0]
    assert item.source == "google"
    assert item.calendar_name == "Google Calendar"
    assert repository.complete(str(item.id)) is None
    assert repository.cancel(str(item.id)) is None
    assert repository.cancel_external("google", "abc123") is True


def test_google_event_creation_is_explicit_and_imported_locally(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database = SQLiteDatabase(tmp_path / "huli.db")
    database.initialize()
    repository = AppointmentRepository(database)
    settings = Settings(environment="test", log_level="CRITICAL", data_dir=tmp_path)
    calendar = GoogleCalendarService(settings, repository, EventBus())
    timezone = ZoneInfo("America/Sao_Paulo")
    start = datetime(2030, 5, 10, 9, 0, tzinfo=timezone)

    class _Events:
        def insert(self, **_kwargs):
            return self

        @staticmethod
        def execute():
            return {"id": "new-google-event"}

    class _Api:
        @staticmethod
        def events():
            return _Events()

    monkeypatch.setattr(calendar, "_load_credentials", lambda _scopes: object())
    monkeypatch.setattr(calendar, "_build_api", lambda _credentials: _Api())

    created = calendar.create_event("Reunião confirmada", start)

    assert created.event_id == "new-google-event"
    item = repository.list_between(start.replace(hour=0), start.replace(hour=23))[0]
    assert item.title == "Reunião confirmada"
    assert item.source == "google"
    assert GoogleCalendarService.is_google_request("agende reunião amanhã às 10 no Google")
