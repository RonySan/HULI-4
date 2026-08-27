"""Formato portátil autenticado para backups privados da Huli."""

from __future__ import annotations

from base64 import b64decode, b64encode
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import secrets
import tempfile
from typing import Any

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


BACKUP_FORMAT = "huli-encrypted-backup"
BACKUP_VERSION = 1
_KDF_N = 2**14
_KDF_R = 8
_KDF_P = 1


class EncryptedFileError(ValueError):
    """Backup inválido, alterado ou aberto com senha incorreta."""


def _b64(value: bytes) -> str:
    return b64encode(value).decode("ascii")


def _unb64(value: object, field: str) -> bytes:
    try:
        return b64decode(str(value), validate=True)
    except Exception as exc:
        raise EncryptedFileError(f"Campo inválido no backup: {field}.") from exc


def _derive_key(password: str, salt: bytes, *, n: int, r: int, p: int) -> bytes:
    if not password:
        raise EncryptedFileError("O backup criptografado exige uma senha não vazia.")
    return hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=n,
        r=r,
        p=p,
        dklen=32,
    )


def _aad(*, purpose: str, owner: str, created_at: str) -> bytes:
    return (
        f"{BACKUP_FORMAT}|{BACKUP_VERSION}|{purpose}|{owner.casefold()}|{created_at}"
    ).encode("utf-8")


def seal_json(
    payload: dict[str, Any],
    *,
    password: str,
    owner: str,
    purpose: str,
) -> dict[str, Any]:
    """Cifra JSON com AES-256-GCM e KDF scrypt independente do banco."""

    created_at = datetime.now(timezone.utc).isoformat()
    salt = secrets.token_bytes(16)
    nonce = secrets.token_bytes(12)
    key = _derive_key(password, salt, n=_KDF_N, r=_KDF_R, p=_KDF_P)
    plaintext = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    ciphertext = AESGCM(key).encrypt(
        nonce,
        plaintext,
        _aad(purpose=purpose, owner=owner, created_at=created_at),
    )
    return {
        "format": BACKUP_FORMAT,
        "version": BACKUP_VERSION,
        "purpose": purpose,
        "owner": owner,
        "created_at": created_at,
        "kdf": {
            "name": "scrypt",
            "salt": _b64(salt),
            "n": _KDF_N,
            "r": _KDF_R,
            "p": _KDF_P,
        },
        "cipher": {
            "name": "AES-256-GCM",
            "nonce": _b64(nonce),
            "ciphertext": _b64(ciphertext),
        },
    }


def open_json(
    envelope: dict[str, Any],
    *,
    password: str,
    expected_owner: str,
    expected_purpose: str | None = None,
) -> dict[str, Any]:
    """Valida metadados e autenticação antes de devolver o conteúdo."""

    if envelope.get("format") != BACKUP_FORMAT or envelope.get("version") != BACKUP_VERSION:
        raise EncryptedFileError("Formato ou versão de backup não reconhecido.")
    owner = str(envelope.get("owner") or "")
    purpose = str(envelope.get("purpose") or "")
    created_at = str(envelope.get("created_at") or "")
    if owner.casefold() != expected_owner.casefold():
        raise EncryptedFileError("Este backup pertence a outro proprietário.")
    if expected_purpose is not None and purpose != expected_purpose:
        raise EncryptedFileError("O arquivo não possui o tipo de backup esperado.")

    kdf = envelope.get("kdf")
    cipher = envelope.get("cipher")
    if not isinstance(kdf, dict) or not isinstance(cipher, dict):
        raise EncryptedFileError("Estrutura criptográfica incompleta no backup.")
    if kdf.get("name") != "scrypt" or cipher.get("name") != "AES-256-GCM":
        raise EncryptedFileError("Algoritmo de backup não reconhecido.")
    try:
        n = int(kdf["n"])
        r = int(kdf["r"])
        p = int(kdf["p"])
    except (KeyError, TypeError, ValueError) as exc:
        raise EncryptedFileError("Parâmetros de derivação inválidos no backup.") from exc
    if (n, r, p) != (_KDF_N, _KDF_R, _KDF_P):
        raise EncryptedFileError("Parâmetros de derivação não suportados.")

    key = _derive_key(
        password,
        _unb64(kdf.get("salt"), "kdf.salt"),
        n=n,
        r=r,
        p=p,
    )
    nonce = _unb64(cipher.get("nonce"), "cipher.nonce")
    ciphertext = _unb64(cipher.get("ciphertext"), "cipher.ciphertext")
    try:
        plaintext = AESGCM(key).decrypt(
            nonce,
            ciphertext,
            _aad(purpose=purpose, owner=owner, created_at=created_at),
        )
    except InvalidTag as exc:
        raise EncryptedFileError(
            "Senha incorreta ou backup alterado/corrompido. Nada foi restaurado."
        ) from exc
    try:
        payload = json.loads(plaintext.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EncryptedFileError("Conteúdo interno inválido no backup.") from exc
    if not isinstance(payload, dict):
        raise EncryptedFileError("O conteúdo do backup precisa ser um objeto JSON.")
    return payload


def write_envelope(path: Path, envelope: dict[str, Any]) -> Path:
    """Grava de forma atômica e restringe permissões quando o SO permite."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(envelope, ensure_ascii=False, sort_keys=True, indent=2)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.",
        suffix=".tmp",
        dir=destination.parent,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(serialized)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        try:
            temporary.chmod(0o600)
        except OSError:
            pass
        os.replace(temporary, destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return destination


def read_envelope(path: Path) -> dict[str, Any]:
    try:
        parsed = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EncryptedFileError("Não foi possível ler um backup válido.") from exc
    if not isinstance(parsed, dict):
        raise EncryptedFileError("Estrutura externa inválida no backup.")
    return parsed


__all__ = [
    "BACKUP_FORMAT",
    "BACKUP_VERSION",
    "EncryptedFileError",
    "open_json",
    "read_envelope",
    "seal_json",
    "write_envelope",
]
