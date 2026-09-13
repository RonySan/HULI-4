"""Sincronização local, somente leitura, do Google Calendar."""

from __future__ import annotations

from base64 import b64decode, b64encode
from dataclasses import dataclass
from datetime import date, datetime, timedelta
import json
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from huli.core.events import EventBus
from huli.infrastructure.config import Settings
from huli.infrastructure.productivity import AppointmentRepository
from huli.security.os_protection import (
    OSKeyProtector,
    OSProtectionError,
    default_os_key_protector,
)


_READ_SCOPES = ("https://www.googleapis.com/auth/calendar.events.readonly",)
_WRITE_SCOPES = ("https://www.googleapis.com/auth/calendar.events",)
_TOKEN_FORMAT = "huli-google-calendar-token"


class GoogleCalendarError(RuntimeError):
    """Falha clara de configuração, autorização ou sincronização Google."""


@dataclass(frozen=True, slots=True)
class GoogleSyncResult:
    imported: int
    updated: int
    cancelled: int
    calendar_name: str = "Google Calendar"

    @property
    def total(self) -> int:
        return self.imported + self.updated

    def summary(self) -> str:
        parts = [f"{self.total} compromisso(s) sincronizado(s)"]
        if self.cancelled:
            parts.append(f"{self.cancelled} cancelado(s)")
        return ", ".join(parts) + "."


@dataclass(frozen=True, slots=True)
class GoogleCreatedEvent:
    """Confirmação de um evento criado explicitamente no Google Calendar."""

    event_id: str
    title: str
    start_at: datetime


class GoogleTokenStore:
    """Armazena o token OAuth protegido por DPAPI da conta atual do Windows."""

    def __init__(self, path: Path, protector: OSKeyProtector | None = None) -> None:
        self.path = Path(path)
        self.protector = protector or default_os_key_protector()

    def exists(self) -> bool:
        return self.path.is_file()

    def load(self) -> dict[str, Any] | None:
        try:
            envelope = json.loads(self.path.read_text(encoding="utf-8"))
            if envelope.get("format") != _TOKEN_FORMAT:
                raise GoogleCalendarError("O token local do Google Calendar não é reconhecido.")
            protected = b64decode(str(envelope["protected_token"]), validate=True)
            raw = self.protector.unprotect(protected)
            payload = json.loads(raw.decode("utf-8"))
        except FileNotFoundError:
            return None
        except (KeyError, OSError, OSProtectionError, UnicodeDecodeError, ValueError) as exc:
            raise GoogleCalendarError(
                "Não consegui abrir o token local do Google Calendar. Conecte novamente."
            ) from exc
        if not isinstance(payload, dict):
            raise GoogleCalendarError("O token local do Google Calendar é inválido.")
        return payload

    def save(self, payload: dict[str, Any]) -> None:
        if self.protector.name != "windows-dpapi-current-user":
            raise GoogleCalendarError(
                "O token do Google Calendar só é salvo com a proteção da conta atual do Windows."
            )
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        try:
            protected = self.protector.protect(raw)
        except OSProtectionError as exc:
            raise GoogleCalendarError(
                "O Windows não conseguiu proteger o token do Google Calendar. "
                "Tente conectar novamente nesta mesma conta do Windows."
            ) from exc
        envelope = {
            "format": _TOKEN_FORMAT,
            "protection": self.protector.name,
            "protected_token": b64encode(protected).decode("ascii"),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(envelope, indent=2), encoding="utf-8")
        temporary.replace(self.path)

    def delete(self) -> None:
        self.path.unlink(missing_ok=True)


class GoogleCalendarService:
    """Importa eventos do calendário principal sem mudar conteúdo no Google."""

    source = "google"

    def __init__(
        self,
        settings: Settings,
        appointments: AppointmentRepository,
        events: EventBus,
        *,
        token_store: GoogleTokenStore | None = None,
    ) -> None:
        self.settings = settings
        self.appointments = appointments
        self.events = events
        self.timezone = ZoneInfo(settings.timezone)
        self.credentials_path = settings.google_calendar_credentials_path
        self.token_store = token_store or GoogleTokenStore(
            settings.data_dir / "secrets" / "google_calendar_token.json"
        )

    @property
    def configured(self) -> bool:
        return self.token_store.exists()

    @property
    def credentials_available(self) -> bool:
        return self.credentials_path.is_file()

    def status_text(self) -> str:
        if self.configured:
            if self.write_authorized:
                return "Google Calendar conectado; leitura e criação confirmada de eventos disponíveis."
            return "Google Calendar conectado; sincronização somente leitura ativa."
        if self.credentials_available:
            return "Google Calendar pronto para conectar; falta autorizar sua conta."
        return "Google Calendar não configurado. Baixe a credencial OAuth de aplicativo para computador."

    @property
    def write_authorized(self) -> bool:
        try:
            payload = self.token_store.load()
        except GoogleCalendarError:
            return False
        scopes = set(payload.get("scopes", ())) if payload else set()
        return set(_WRITE_SCOPES).issubset(scopes)

    @staticmethod
    def is_google_request(text: str) -> bool:
        normalized = " ".join(str(text or "").casefold().split())
        return (
            "google calendar" in normalized
            or " no google" in normalized
            or " para o google" in normalized
        )

    def connect(self, *, write_access: bool = False) -> GoogleSyncResult:
        if not self.credentials_path.is_file():
            raise GoogleCalendarError(
                "Não encontrei credentials/google_calendar_oauth.json. "
                "Crie a credencial OAuth Desktop no Google Cloud e salve o arquivo nesse local."
            )
        try:
            from google_auth_oauthlib.flow import InstalledAppFlow
        except ImportError as exc:
            raise GoogleCalendarError(
                "Instale a integração com INSTALAR_GOOGLE_CALENDAR.bat antes de conectar."
            ) from exc
        flow = InstalledAppFlow.from_client_secrets_file(
            str(self.credentials_path),
            scopes=_WRITE_SCOPES if write_access else _READ_SCOPES,
        )
        credentials = flow.run_local_server(port=0)
        self.token_store.save(json.loads(credentials.to_json()))
        self.events.publish("google.calendar.connected", {"mode": "read-only"})
        return self.sync()

    def disconnect(self) -> None:
        self.token_store.delete()
        self.events.publish("google.calendar.disconnected", {})

    def sync(self, *, now: datetime | None = None) -> GoogleSyncResult:
        credentials = self._load_credentials(_READ_SCOPES)
        service = self._build_api(credentials)
        reference = (now or datetime.now(self.timezone)).astimezone(self.timezone)
        start = reference - timedelta(days=1)
        end = reference + timedelta(days=self.settings.google_calendar_sync_days)
        response = service.events().list(
            calendarId="primary",
            timeMin=start.isoformat(),
            timeMax=end.isoformat(),
            singleEvents=True,
            showDeleted=True,
            orderBy="startTime",
            maxResults=1000,
        ).execute()
        imported = updated = cancelled = 0
        for event in response.get("items", ()):
            remote_id = str(event.get("id") or "").strip()
            if not remote_id:
                continue
            if event.get("status") == "cancelled":
                if self.appointments.cancel_external(self.source, remote_id):
                    cancelled += 1
                continue
            title = " ".join(str(event.get("summary") or "(sem título)").split())
            start_at = self._event_datetime(event.get("start") or {})
            end_at = self._event_datetime(event.get("end") or {})
            action = self.appointments.upsert_external(
                source=self.source,
                external_id=remote_id,
                title=title,
                start_at=start_at,
                end_at=end_at,
                calendar_name="Google Calendar",
            )
            if action == "created":
                imported += 1
            elif action == "updated":
                updated += 1
        result = GoogleSyncResult(imported, updated, cancelled)
        self.events.publish(
            "google.calendar.synced",
            {
                "imported": imported,
                "updated": updated,
                "cancelled": cancelled,
                "mode": "read-only",
            },
        )
        return result

    def create_event(
        self,
        title: str,
        start_at: datetime,
        *,
        end_at: datetime | None = None,
    ) -> GoogleCreatedEvent:
        """Cria um evento somente depois da confirmação visual da interface."""
        normalized_title = " ".join(str(title or "").split())
        if not normalized_title:
            raise GoogleCalendarError("Informe o assunto do compromisso antes de confirmar.")
        local_start = start_at.astimezone(self.timezone)
        local_end = (end_at or (local_start + timedelta(hours=1))).astimezone(self.timezone)
        if local_end <= local_start:
            raise GoogleCalendarError("O fim do compromisso precisa ser depois do início.")
        credentials = self._load_credentials(_WRITE_SCOPES)
        service = self._build_api(credentials)
        try:
            created = service.events().insert(
                calendarId="primary",
                body={
                    "summary": normalized_title,
                    "start": {"dateTime": local_start.isoformat(), "timeZone": self.settings.timezone},
                    "end": {"dateTime": local_end.isoformat(), "timeZone": self.settings.timezone},
                },
            ).execute()
        except Exception as exc:
            raise GoogleCalendarError(
                "Não consegui criar o evento no Google Calendar. Nada foi salvo pela Huli."
            ) from exc
        event_id = str(created.get("id") or "").strip()
        if not event_id:
            raise GoogleCalendarError("O Google Calendar não confirmou um identificador para o evento.")
        self.appointments.upsert_external(
            source=self.source,
            external_id=event_id,
            title=normalized_title,
            start_at=local_start,
            end_at=local_end,
            calendar_name="Google Calendar",
        )
        self.events.publish("google.calendar.event_created", {"event_id": event_id})
        return GoogleCreatedEvent(event_id, normalized_title, local_start)

    def _load_credentials(self, scopes: tuple[str, ...]):
        payload = self.token_store.load()
        if payload is None:
            raise GoogleCalendarError("Google Calendar ainda não está conectado.")
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
        except ImportError as exc:
            raise GoogleCalendarError(
                "Instale a integração com INSTALAR_GOOGLE_CALENDAR.bat antes de sincronizar."
            ) from exc
        credentials = Credentials.from_authorized_user_info(payload, scopes=scopes)
        if not credentials.has_scopes(scopes):
            raise GoogleCalendarError(
                "Essa conta tem somente permissão de leitura. Execute "
                "AUTORIZAR_GOOGLE_CALENDAR_ESCRITA.bat para permitir criação confirmada de eventos."
            )
        if credentials.expired:
            if not credentials.refresh_token:
                raise GoogleCalendarError("A autorização do Google expirou. Conecte novamente.")
            credentials.refresh(Request())
            self.token_store.save(json.loads(credentials.to_json()))
        return credentials

    @staticmethod
    def _build_api(credentials):
        try:
            from googleapiclient.discovery import build
        except ImportError as exc:
            raise GoogleCalendarError(
                "Instale a integração com INSTALAR_GOOGLE_CALENDAR.bat antes de sincronizar."
            ) from exc
        return build("calendar", "v3", credentials=credentials, cache_discovery=False)

    def _event_datetime(self, payload: dict[str, Any]) -> datetime:
        raw_datetime = payload.get("dateTime")
        if raw_datetime:
            value = str(raw_datetime).replace("Z", "+00:00")
            return datetime.fromisoformat(value).astimezone(self.timezone)
        raw_date = payload.get("date")
        if raw_date:
            day = date.fromisoformat(str(raw_date))
            return datetime(day.year, day.month, day.day, tzinfo=self.timezone)
        raise GoogleCalendarError("Recebi um evento do Google Calendar sem horário válido.")
