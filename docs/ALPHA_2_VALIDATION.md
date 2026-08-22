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

## Teste manual — proprietário

Depois da validação automatizada:

```powershell
.\.venv\Scripts\Activate.ps1
python main.py
```

Na primeira execução:

1. informar o nome do proprietário;
2. deixar a senha vazia para usar sem senha **ou** definir uma senha com pelo menos 4 caracteres;
3. entrar como proprietário;
4. executar `ping`;
5. encerrar com `sair`.

Quando o proprietário foi criado sem senha, a Huli não deve pedir senha nas execuções seguintes para esse usuário.

## Teste manual — visitante

Também validar o modo visitante:

1. iniciar `python main.py`;
2. deixar `Usuário` vazio ou informar um nome não cadastrado;
3. confirmar a mensagem de acesso como visitante;
4. executar `ping`, que deve funcionar;
5. tentar `abrir calculadora`, que deve ser bloqueado por exigir proprietário;
6. encerrar com `sair`.

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

A senha também pode ser vazia para um proprietário configurado sem senha nesta fase local. Usuário desconhecido não recebe acesso protegido pela API.

## Critério final

A Fase 0 só é concluída quando o Windows comprovar o fluxo:

```text
Huli inicia
↓
identifica proprietário ou visitante
↓
aplica permissões
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
