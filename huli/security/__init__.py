"""Autenticação, autorização e políticas de segurança da Huli."""

from huli.security.auth import AuthenticatedUser, AuthenticationError, AuthService
from huli.security.encrypted_file import EncryptedFileError
from huli.security.journal_vault import (
    JournalVault,
    JournalVaultError,
    JournalVaultIntegrityError,
    JournalVaultLockedError,
    VaultUnlockResult,
)
from huli.security.policy import SecurityPolicy
from huli.security.privacy import PRIVATE_JOURNAL_REDACTION, is_private_journal_text

__all__ = [
    "AuthenticatedUser",
    "AuthenticationError",
    "AuthService",
    "EncryptedFileError",
    "JournalVault",
    "JournalVaultError",
    "JournalVaultIntegrityError",
    "JournalVaultLockedError",
    "PRIVATE_JOURNAL_REDACTION",
    "SecurityPolicy",
    "VaultUnlockResult",
    "is_private_journal_text",
]
