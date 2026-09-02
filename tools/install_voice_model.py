"""Instala somente o modelo oficial português, sem sobrescrever modelo existente."""

from __future__ import annotations

from pathlib import Path, PurePosixPath
import shutil
import tempfile
from urllib.request import urlopen
import zipfile

from huli.infrastructure.config import APP_ROOT

URL = "https://alphacephei.com/vosk/models/vosk-model-small-pt-0.3.zip"
MODEL_DIRECTORY = "vosk-model-small-pt-0.3"


def main() -> int:
    target = APP_ROOT / "models" / "vosk-pt"
    if target.exists():
        print(f"Modelo existente preservado: {target}")
        return 0 if any(path.is_file() for path in (target / "final.mdl", target / "am" / "final.mdl")) else 1
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="huli-model-", dir=target.parent) as temp:
        staging = Path(temp)
        archive_path = staging / "model.zip"
        print("Baixando uma vez o modelo português oficial. A escuta posterior funciona offline.")
        with urlopen(URL, timeout=60) as response, archive_path.open("wb") as output:
            size = 0
            while chunk := response.read(1024 * 1024):
                size += len(chunk)
                if size > 64 * 1024 * 1024:
                    raise ValueError("Download excedeu o tamanho esperado.")
                output.write(chunk)
        with zipfile.ZipFile(archive_path) as archive:
            entries = archive.infolist()
            if sum(item.file_size for item in entries) > 300 * 1024 * 1024:
                raise ValueError("Arquivo extraído excede o tamanho esperado.")
            for item in entries:
                name = PurePosixPath(item.filename)
                if (name.is_absolute() or ".." in name.parts or ":" in item.filename
                        or "\\" in item.filename or not name.parts
                        or name.parts[0] != MODEL_DIRECTORY
                        or (item.external_attr >> 16) & 0o170000 == 0o120000):
                    raise ValueError("O arquivo do modelo contém um caminho não permitido.")
            archive.extractall(staging)
        extracted = staging / MODEL_DIRECTORY
        if not any(path.is_file() for path in (extracted / "final.mdl", extracted / "am" / "final.mdl")):
            raise ValueError("O arquivo não contém o modelo esperado.")
        shutil.copytree(extracted, target)
    print(f"Modelo instalado em {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
