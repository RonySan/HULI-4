# Huli 4.0.0-alpha.2 — Validação da Fase 0

Este checklist deve ser executado antes de concluir a Fase 0.

## Validação automatizada no Windows

Atualize a branch:

```powershell
cd C:\HULI4
git checkout phase-0-foundation
git pull
```

Depois execute um único comando:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\VALIDAR_FASE0.ps1
```

O script usa o `.venv` existente e executa:

1. verificação do Python;
2. instalação/atualização de `.[dev]`;
3. Ruff;
4. Pytest;
5. `tools/validate_phase0.py`.

O validador automatizado usa um banco temporário e não altera `data/huli.db` do usuário.

Resultado esperado no final:

```text
FASE 0: validação automatizada concluída com sucesso.
FASE 0 APROVADA NESTE COMPUTADOR
```

## Teste manual final do terminal

Depois da validação automatizada:

```powershell
.\.venv\Scripts\Activate.ps1
python main.py
```

Validar:

1. setup do proprietário na primeira execução, quando ainda não existir;
2. login;
3. `ping` atendido pela `FoundationSkill`;
4. uma frase sem Skill retornando fallback controlado;
5. `sair` encerrando e revogando a sessão.

## Persistência real local

Após uma interação manual, deve existir:

```text
C:\HULI4\data\huli.db
```

O banco não deve ser commitado no Git.

## API manual opcional de inspeção

A API já é coberta pelo validador automatizado e pelos testes. Para inspecioná-la manualmente:

```powershell
python -m huli.api
```

Abrir:

```text
http://127.0.0.1:8765/health
http://127.0.0.1:8765/docs
```

## Critério final

A Fase 0 só é concluída quando o Windows comprovar o fluxo:

```text
Huli inicia
↓
autentica
↓
recebe mensagem
↓
Kernel coordena
↓
Skill responde
↓
EventBus publica
↓
interação é persistida
```
