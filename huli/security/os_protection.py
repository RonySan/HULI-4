"""Proteção adicional de pequenos segredos pelo sistema operacional.

No Windows, o envelope já protegido pela senha do proprietário recebe uma
segunda camada com DPAPI vinculada à conta atual. Em outros sistemas, a
proteção por senha continua sendo a camada portátil obrigatória.
"""

from __future__ import annotations

from ctypes import POINTER, Structure, byref, cast, create_string_buffer, string_at
from ctypes import wintypes
import ctypes
import sys
from typing import Protocol


class OSProtectionError(RuntimeError):
    """O sistema operacional não conseguiu proteger ou abrir um envelope."""


class OSKeyProtector(Protocol):
    name: str

    def protect(self, data: bytes) -> bytes: ...

    def unprotect(self, data: bytes) -> bytes: ...


class PasswordOnlyProtector:
    """Marcador portátil: o conteúdo já está cifrado pela senha."""

    name = "password-only"

    @staticmethod
    def protect(data: bytes) -> bytes:
        return bytes(data)

    @staticmethod
    def unprotect(data: bytes) -> bytes:
        return bytes(data)


if sys.platform == "win32":

    class _DataBlob(Structure):
        _fields_ = [
            ("cbData", wintypes.DWORD),
            ("pbData", POINTER(ctypes.c_ubyte)),
        ]


class WindowsDPAPIProtector:
    """Usa DPAPI no escopo do usuário atual sem armazenar outra chave."""

    name = "windows-dpapi-current-user"
    _description = "HULI Journal Vault"
    _entropy = b"HULI Journal Vault v1"
    _ui_forbidden = 0x1

    def __init__(self) -> None:
        if sys.platform != "win32":
            raise OSProtectionError("DPAPI está disponível somente no Windows.")
        self._crypt32 = ctypes.windll.crypt32
        self._kernel32 = ctypes.windll.kernel32
        self._crypt32.CryptProtectData.argtypes = [
            POINTER(_DataBlob),
            wintypes.LPCWSTR,
            POINTER(_DataBlob),
            ctypes.c_void_p,
            ctypes.c_void_p,
            wintypes.DWORD,
            POINTER(_DataBlob),
        ]
        self._crypt32.CryptProtectData.restype = wintypes.BOOL
        self._crypt32.CryptUnprotectData.argtypes = [
            POINTER(_DataBlob),
            POINTER(wintypes.LPWSTR),
            POINTER(_DataBlob),
            ctypes.c_void_p,
            ctypes.c_void_p,
            wintypes.DWORD,
            POINTER(_DataBlob),
        ]
        self._crypt32.CryptUnprotectData.restype = wintypes.BOOL
        self._kernel32.LocalFree.argtypes = [ctypes.c_void_p]
        self._kernel32.LocalFree.restype = ctypes.c_void_p

    @staticmethod
    def _blob(data: bytes) -> tuple[object, object]:
        buffer = create_string_buffer(data, len(data))
        blob = _DataBlob(
            len(data),
            cast(buffer, POINTER(ctypes.c_ubyte)),
        )
        return blob, buffer

    def protect(self, data: bytes) -> bytes:
        input_blob, input_buffer = self._blob(bytes(data))
        entropy_blob, entropy_buffer = self._blob(self._entropy)
        output_blob = _DataBlob()
        success = self._crypt32.CryptProtectData(
            byref(input_blob),
            self._description,
            byref(entropy_blob),
            None,
            None,
            self._ui_forbidden,
            byref(output_blob),
        )
        del input_buffer, entropy_buffer
        if not success:
            raise OSProtectionError("O Windows não conseguiu proteger a chave do diário.")
        try:
            return bytes(string_at(output_blob.pbData, output_blob.cbData))
        finally:
            self._kernel32.LocalFree(output_blob.pbData)

    def unprotect(self, data: bytes) -> bytes:
        input_blob, input_buffer = self._blob(bytes(data))
        entropy_blob, entropy_buffer = self._blob(self._entropy)
        output_blob = _DataBlob()
        description = wintypes.LPWSTR()
        success = self._crypt32.CryptUnprotectData(
            byref(input_blob),
            byref(description),
            byref(entropy_blob),
            None,
            None,
            self._ui_forbidden,
            byref(output_blob),
        )
        del input_buffer, entropy_buffer
        if not success:
            raise OSProtectionError(
                "A chave do diário pertence a outra conta do Windows ou foi corrompida."
            )
        try:
            return bytes(string_at(output_blob.pbData, output_blob.cbData))
        finally:
            if description:
                self._kernel32.LocalFree(description)
            self._kernel32.LocalFree(output_blob.pbData)


def default_os_key_protector() -> OSKeyProtector:
    if sys.platform == "win32":
        return WindowsDPAPIProtector()
    return PasswordOnlyProtector()


__all__ = [
    "OSKeyProtector",
    "OSProtectionError",
    "PasswordOnlyProtector",
    "WindowsDPAPIProtector",
    "default_os_key_protector",
]
