# Huli 4.0.0-alpha.2 — Validação da Fase 0

Este checklist deve ser executado antes de concluir a Fase 0.

## Atualização

```powershell
cd C:\HULI4
git checkout phase-0-foundation
git pull
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

## Qualidade

```powershell
python -m ruff check .
python -m pytest
```

Ambos precisam terminar sem erro.

## Terminal

```powershell
python main.py
```

Na primeira execução:

1. criar o usuário proprietário;
2. criar uma senha com pelo menos 10 caracteres;
3. autenticar;
4. executar `ping`;
5. executar uma frase sem Skill;
6. encerrar com `sair`.

`ping` deve ser atendido pela `FoundationSkill`. Uma frase sem Skill deve retornar fallback controlado.

## Persistência

Após uma interação, o arquivo abaixo deve existir:

```text
C:\HULI4\data\huli.db
```

O banco não deve ser commitado no Git.

## API

Em outro PowerShell, com o ambiente ativo:

```powershell
python -m huli.api
```

Verificar:

```text
http://127.0.0.1:8765/health
http://127.0.0.1:8765/docs
```

Pelo `/docs`, validar setup/login quando aplicável e enviar `ping` para `/v1/messages` usando Bearer token.

## Critério final

A Fase 0 só é concluída quando terminal e API comprovarem o fluxo:

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
