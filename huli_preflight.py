"""Verificação leve da instalação antes de iniciar a Huli.

Este módulo usa apenas a biblioteca padrão para continuar funcionando quando
uma dependência do projeto estiver ausente. Ele não acessa dados pessoais.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from importlib.util import find_spec
import os
from pathlib import Path
import sys


APP_ROOT = Path(__file__).resolve().parent
_CORE_MODULES = {
    "cryptography": "cryptography",
    "fastapi": "fastapi",
    "uvicorn": "uvicorn",
    "tzdata": "tzdata",
}


@dataclass(frozen=True, slots=True)
class PreflightReport:
    errors: tuple[str, ...]
    warnings: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.errors


def _configured_path(variable: str, default: str) -> Path:
    raw = os.environ.get(variable, default).strip() or default
    path = Path(raw).expanduser()
    return path.resolve() if path.is_absolute() else (APP_ROOT / path).resolve()


def _module_available(name: str) -> bool:
    try:
        return find_spec(name) is not None
    except (ImportError, AttributeError, ValueError):
        return False


def inspect_installation(*, include_voice: bool = False) -> PreflightReport:
    errors: list[str] = []
    warnings: list[str] = []

    if sys.version_info[:2] != (3, 11):
        errors.append(
            "A Huli exige Python 3.11; o ambiente atual usa "
            f"{sys.version_info.major}.{sys.version_info.minor}."
        )

    missing_core = [
        label for module, label in _CORE_MODULES.items() if not _module_available(module)
    ]
    if missing_core:
        errors.append("Dependências principais ausentes: " + ", ".join(missing_core) + ".")

    if include_voice:
        if not _module_available("sounddevice"):
            errors.append("A biblioteca do microfone (sounddevice) não está instalada.")
        if not _module_available("pocketsphinx"):
            errors.append("O detector local do chamado Huli/Ruli não está instalado.")

        whisper_path = _configured_path(
            "HULI_VOICE_WHISPER_MODEL_PATH",
            "models/whisper-small",
        )
        whisper_files = ("model.bin", "config.json", "tokenizer.json")
        whisper_ready = _module_available("faster_whisper") and all(
            (whisper_path / filename).is_file() for filename in whisper_files
        )

        vosk_path = _configured_path("HULI_VOICE_MODEL_PATH", "models/vosk-pt")
        vosk_ready = _module_available("vosk") and any(
            candidate.is_file()
            for candidate in (vosk_path / "final.mdl", vosk_path / "am" / "final.mdl")
        )
        if not whisper_ready and not vosk_ready:
            errors.append(
                "Nenhum reconhecedor local completo foi encontrado "
                "(Whisper ou Vosk)."
            )
        elif not whisper_ready:
            warnings.append(
                "Whisper melhorado indisponível; a Huli usará o reconhecimento Vosk."
            )

    if not errors:
        try:
            __import__("huli.bootstrap")
        except Exception as exc:
            errors.append(
                "A inicialização interna falhou: "
                f"{exc.__class__.__name__}: {exc}"
            )

    return PreflightReport(tuple(errors), tuple(warnings))


def format_report(
    report: PreflightReport,
    *,
    include_voice: bool = False,
) -> str:
    if report.ok:
        lines = [
            "Huli: instalação principal e voz local verificadas."
            if include_voice
            else "Huli: instalação principal verificada."
        ]
    else:
        lines = ["Huli: não foi possível iniciar com segurança."]
    lines.extend(f"- ERRO: {item}" for item in report.errors)
    lines.extend(f"- AVISO: {item}" for item in report.warnings)
    if report.errors:
        lines.append(
            "Reparo sugerido: .venv\\Scripts\\python.exe -m pip install -e ."
        )
        lines.append(
            "Para voz local, execute também INSTALAR_VOZ_MELHORADA.bat."
        )
    return "\n".join(lines)


def ensure_core() -> None:
    """Interrompe uma inicialização direta com uma mensagem compreensível."""
    report = inspect_installation()
    if not report.ok:
        raise SystemExit(format_report(report))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verifica a instalação local da Huli.")
    parser.add_argument(
        "--voice",
        action="store_true",
        help="exige também microfone, ativação e um reconhecedor local",
    )
    args = parser.parse_args(argv)
    report = inspect_installation(include_voice=args.voice)
    print(format_report(report, include_voice=args.voice))
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
