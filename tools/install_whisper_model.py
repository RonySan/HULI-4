"""Instala uma cópia local e versionada do Whisper Small para a Huli."""

from __future__ import annotations

from pathlib import Path
import shutil
import tempfile

from huli.infrastructure.config import APP_ROOT


MODEL_ID = "Systran/faster-whisper-small"
MODEL_REVISION = "2ec96c5472da50d38d40c0cfe0602af2e94b4c8a"
REQUIRED_FILES = ("model.bin", "config.json", "tokenizer.json")


def _valid_model(path: Path) -> bool:
    if not all((path / name).is_file() for name in REQUIRED_FILES):
        return False
    size = (path / "model.bin").stat().st_size
    return 400 * 1024 * 1024 <= size <= 600 * 1024 * 1024


def main() -> int:
    target = APP_ROOT / "models" / "whisper-small"
    if _valid_model(target):
        print(f"Modelo Whisper existente preservado: {target}")
        return 0
    if target.exists():
        print(
            f"Modelo incompleto encontrado em {target}. "
            "Não removi arquivos automaticamente; renomeie essa pasta e tente novamente."
        )
        return 1

    try:
        from faster_whisper.utils import download_model
    except ImportError:
        print(
            "Faster Whisper não está instalado. Execute "
            "INSTALAR_VOZ_MELHORADA.bat."
        )
        return 1

    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="huli-whisper-", dir=target.parent) as temp:
        staging = Path(temp) / "model"
        print(
            "Baixando uma vez o Whisper Small (aproximadamente 490 MB). "
            "Depois disso a transcrição funciona offline."
        )
        download_model(
            MODEL_ID,
            output_dir=str(staging),
            revision=MODEL_REVISION,
        )
        if not _valid_model(staging):
            raise ValueError("O download não contém um modelo Whisper Small válido.")
        shutil.move(str(staging), str(target))
    print(f"Modelo Whisper instalado em {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
