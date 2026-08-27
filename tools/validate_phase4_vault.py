"""Validação ponta a ponta da Fase 4.2: cofre pessoal seguro."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from huli import __version__
from huli.bootstrap import build_runtime
from huli.infrastructure import Settings
from huli.security import AuthenticationError, JournalVaultLockedError


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def run_validation() -> None:
    print(f"Validando cofre pessoal seguro em {__version__}...")
    password = "senha-segura-123"
    new_password = "senha-nova-456"

    with TemporaryDirectory(prefix="huli-vault-") as temp_dir:
        settings = Settings(
            environment="validation",
            log_level="CRITICAL",
            data_dir=Path(temp_dir) / "data",
            journal_lock_minutes=1,
        )
        runtime = build_runtime(settings)
        runtime.auth.create_owner("rony", password)
        _user, old_token = runtime.auth.authenticate("rony", password)
        phrase = "relato privado cifrado da evolução safira"
        entry = runtime.journal.create(
            owner="rony",
            content=phrase,
            mood="feliz",
            tags=("huli", "evolução"),
        )

        require(runtime.database.schema_version() >= 8, "Schema 8 não está ativo.")
        with runtime.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM journal_entries WHERE id = ?",
                (entry.id,),
            ).fetchone()
        require(row is not None, "Entrada cifrada não foi persistida.")
        require(row["content"] == "", "Conteúdo permaneceu em texto no SQLite.")
        require(row["search_text"] == "", "Índice de busca permaneceu em texto.")
        require(bool(row["content_ciphertext"]), "Ciphertext do conteúdo está vazio.")
        require(row["crypto_version"] == 1, "Versão criptográfica inválida.")

        backup = runtime.journal_backups.create_backup(
            owner="rony",
            password=password,
        )
        require(backup.exists(), "Backup portátil não foi criado.")
        require(
            phrase.encode("utf-8") not in backup.read_bytes(),
            "Backup contém texto privado legível.",
        )

        runtime.auth.revoke_token(old_token)
        try:
            runtime.journal.recent(owner="rony")
        except JournalVaultLockedError:
            pass
        else:
            raise RuntimeError("Logout não bloqueou a chave do diário.")

        runtime.auth.authenticate("rony", password)
        require(
            runtime.journal.search(owner="rony", query="safira")[0].content == phrase,
            "Reabertura ou pesquisa por índice cego falhou.",
        )
        runtime.auth.set_password(
            "rony",
            new_password,
            current_password=password,
        )
        try:
            runtime.auth.authenticate("rony", password)
        except AuthenticationError:
            pass
        else:
            raise RuntimeError("Senha anterior continuou válida.")
        runtime.auth.authenticate("rony", new_password)
        require(
            runtime.journal.recent(owner="rony")[0].content == phrase,
            "Troca de senha perdeu a entrada cifrada.",
        )

    print("FASE 4.2: cofre pessoal seguro validado com sucesso.")


def main() -> int:
    try:
        run_validation()
        return 0
    except Exception as exc:
        print(f"FASE 4.2: FALHA - {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
