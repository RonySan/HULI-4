"""Descoberta e abertura segura de aplicativos instalados no Windows."""

from __future__ import annotations

from dataclasses import dataclass
from difflib import get_close_matches
from pathlib import Path
import os
import re
import sys
from typing import Callable, Iterable, Mapping
import unicodedata


class ApplicationLaunchError(ValueError):
    """Aplicativo ausente, ambíguo ou inseguro para abertura."""


@dataclass(frozen=True, slots=True)
class InstalledApplication:
    name: str
    target: Path
    source: str


def _application_key(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", str(value or "").casefold())
    plain = "".join(
        char for char in decomposed if not unicodedata.combining(char)
    )
    plain = re.sub(r"\.(?:exe|lnk)$", "", plain)
    return " ".join(re.sub(r"[^a-z0-9]+", " ", plain).split())


class ApplicationLauncher:
    """Resolve nomes locais e abre somente alvos instalados conhecidos."""

    _ALLOWED_SUFFIXES = {".exe", ".lnk"}
    _FORBIDDEN_QUERY = re.compile(r"[\\/:|&;<>`$%\r\n]")

    def __init__(
        self,
        *,
        start_menu_roots: Iterable[Path] | None = None,
        aliases: Mapping[str, Path] | None = None,
        opener: Callable[[str], None] | None = None,
        platform_name: str | None = None,
        include_registry: bool | None = None,
    ) -> None:
        self.platform_name = platform_name or sys.platform
        self.start_menu_roots = (
            tuple(Path(path) for path in start_menu_roots)
            if start_menu_roots is not None
            else self._default_start_menu_roots()
        )
        self.aliases = dict(aliases) if aliases is not None else self._system_aliases()
        self._opener = opener or self._startfile
        self.include_registry = (
            start_menu_roots is None
            if include_registry is None
            else include_registry
        )

    def launch(self, requested_name: str) -> InstalledApplication:
        query = self._validate_query(requested_name)
        applications = self.discover()
        match = self._resolve(query, applications)
        try:
            self._opener(str(match.target))
        except OSError as exc:
            raise ApplicationLaunchError(
                f"O Windows não conseguiu abrir {match.name}."
            ) from exc
        return match

    def discover(self) -> tuple[InstalledApplication, ...]:
        if not self.platform_name.casefold().startswith("win"):
            return ()
        found: dict[tuple[str, str], InstalledApplication] = {}
        for name, target in self.aliases.items():
            self._add(found, name, Path(target), "sistema")
        for root in self.start_menu_roots:
            if not root.is_dir():
                continue
            try:
                shortcuts = root.rglob("*.lnk")
                for shortcut in shortcuts:
                    self._add(found, shortcut.stem, shortcut, "menu iniciar")
            except OSError:
                continue
        if self.include_registry:
            for application in self._registry_applications():
                self._add(found, application.name, application.target, application.source)
        return tuple(
            sorted(found.values(), key=lambda item: _application_key(item.name))
        )

    @classmethod
    def _add(
        cls,
        found: dict[tuple[str, str], InstalledApplication],
        name: str,
        target: Path,
        source: str,
    ) -> None:
        try:
            resolved = target.expanduser().resolve()
        except OSError:
            return
        if (
            resolved.suffix.casefold() not in cls._ALLOWED_SUFFIXES
            or not resolved.is_file()
        ):
            return
        key = _application_key(name)
        if key:
            found[(key, str(resolved).casefold())] = InstalledApplication(
                name=" ".join(name.split()),
                target=resolved,
                source=source,
            )

    @classmethod
    def _validate_query(cls, value: str) -> str:
        raw = " ".join(str(value or "").split()).strip(" .,!?")
        if not raw:
            raise ApplicationLaunchError("Diga o nome do programa que deseja abrir.")
        if cls._FORBIDDEN_QUERY.search(raw) or raw.casefold().endswith(
            (".bat", ".cmd", ".ps1", ".vbs", ".js", ".url")
        ):
            raise ApplicationLaunchError(
                "Por segurança, informe apenas o nome de um programa instalado."
            )
        return raw

    @staticmethod
    def _resolve(
        query: str,
        applications: tuple[InstalledApplication, ...],
    ) -> InstalledApplication:
        query_key = _application_key(query)
        exact = [app for app in applications if _application_key(app.name) == query_key]
        candidates = exact or [
            app
            for app in applications
            if query_key in _application_key(app.name)
            or _application_key(app.name) in query_key
        ]
        unique: dict[str, InstalledApplication] = {
            str(app.target).casefold(): app for app in candidates
        }
        if len(unique) == 1:
            return next(iter(unique.values()))
        if len(unique) > 1:
            names = ", ".join(sorted({app.name for app in unique.values()})[:5])
            raise ApplicationLaunchError(
                f"Encontrei mais de um programa parecido: {names}. Seja mais específico."
            )
        available = {_application_key(app.name): app.name for app in applications}
        suggestions = get_close_matches(query_key, available, n=3, cutoff=0.55)
        hint = (
            " Talvez você queira: "
            + ", ".join(available[item] for item in suggestions)
            + "."
            if suggestions
            else ""
        )
        raise ApplicationLaunchError(
            f"Não encontrei o programa “{query}” instalado.{hint}"
        )

    @staticmethod
    def _default_start_menu_roots() -> tuple[Path, ...]:
        roots: list[Path] = []
        for variable in ("PROGRAMDATA", "APPDATA"):
            base = os.environ.get(variable)
            if base:
                roots.append(Path(base) / "Microsoft" / "Windows" / "Start Menu" / "Programs")
        return tuple(roots)

    @staticmethod
    def _system_aliases() -> dict[str, Path]:
        windows = Path(os.environ.get("SystemRoot", r"C:\Windows"))
        system32 = windows / "System32"
        return {
            "bloco de notas": system32 / "notepad.exe",
            "notepad": system32 / "notepad.exe",
            "calculadora": system32 / "calc.exe",
            "explorador de arquivos": windows / "explorer.exe",
            "explorer": windows / "explorer.exe",
            "paint": system32 / "mspaint.exe",
        }

    def _registry_applications(self) -> tuple[InstalledApplication, ...]:
        if not self.platform_name.casefold().startswith("win"):
            return ()
        try:
            import winreg
        except ImportError:
            return ()

        records: list[InstalledApplication] = []
        key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"
        for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            try:
                with winreg.OpenKey(hive, key_path) as root:
                    count = winreg.QueryInfoKey(root)[0]
                    for index in range(count):
                        subkey_name = winreg.EnumKey(root, index)
                        try:
                            with winreg.OpenKey(root, subkey_name) as subkey:
                                raw_target = str(winreg.QueryValue(subkey, None))
                        except OSError:
                            continue
                        target = self._executable_from_registry(raw_target)
                        if target is not None:
                            records.append(
                                InstalledApplication(
                                    name=Path(subkey_name).stem,
                                    target=target,
                                    source="registro do Windows",
                                )
                            )
            except OSError:
                continue
        return tuple(records)

    @staticmethod
    def _executable_from_registry(value: str) -> Path | None:
        raw = value.strip()
        if raw.startswith('"'):
            end = raw.find('"', 1)
            raw = raw[1:end] if end > 1 else ""
        else:
            match = re.match(r"(?i)^(.+?\.exe)(?:\s|$)", raw)
            raw = match.group(1) if match else ""
        target = Path(os.path.expandvars(raw)) if raw else None
        if (
            target is None
            or not target.is_absolute()
            or target.suffix.casefold() != ".exe"
        ):
            return None
        return target

    @staticmethod
    def _startfile(target: str) -> None:
        if not hasattr(os, "startfile"):
            raise OSError("A abertura local está disponível somente no Windows.")
        os.startfile(target)  # type: ignore[attr-defined]


__all__ = [
    "ApplicationLaunchError",
    "ApplicationLauncher",
    "InstalledApplication",
]
