"""Registro mínimo e privado da inicialização automática da Huli."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path


@dataclass(frozen=True, slots=True)
class StartupState:
    status: str
    updated_at: str
    detail: str = ""


class StartupReporter:
    """Guarda o último resultado do arranque sem registrar conversas ou dados pessoais."""

    def __init__(self, data_dir: Path) -> None:
        self.path = data_dir / "desktop_startup.json"

    def starting(self) -> StartupState:
        return self._write("starting", "Inicialização automática em andamento.")

    def ready(self) -> StartupState:
        return self._write("ready", "Painel residente iniciado.")

    def failed(self, error: BaseException) -> StartupState:
        detail = " ".join(str(error).split())[:300]
        message = error.__class__.__name__
        if detail:
            message = f"{message}: {detail}"
        return self._write("failed", message)

    def read(self) -> StartupState | None:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            return StartupState(
                status=str(payload["status"]),
                updated_at=str(payload["updated_at"]),
                detail=str(payload.get("detail", "")),
            )
        except (FileNotFoundError, KeyError, OSError, TypeError, ValueError):
            return None

    def _write(self, status: str, detail: str) -> StartupState:
        state = StartupState(
            status=status,
            updated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            detail=detail,
        )
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix(".tmp")
            temporary.write_text(
                json.dumps(asdict(state), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            temporary.replace(self.path)
        except OSError:
            pass
        return state
