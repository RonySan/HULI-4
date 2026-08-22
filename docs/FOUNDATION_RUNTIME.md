# Fundação de Runtime — Fase 0

Este documento registra os componentes implementados após o Kernel mínimo.

## Skill Registry

O `SkillRegistry` implementa o contrato `KernelHandler`. O Kernel conhece apenas esse contrato e não importa Skills concretas.

Fluxo atual:

```text
entrada
  ↓
Kernel
  ↓
SkillRegistry
  ↓
Skill compatível
  ↓
KernelResponse
```

A `FoundationSkill` existe apenas para validar a arquitetura durante a Fase 0 e reconhece comandos técnicos como `ping`, `status`, `status huli` e `teste`.

## Eventos internos

O `EventBus` é síncrono e desacoplado. O Kernel publica atualmente:

- `kernel.request.received`
- `kernel.response.created`

Memória, métricas, logging avançado e agentes futuros poderão assinar esses eventos sem criar dependência dentro do Kernel.

## Configuração

`Settings` é imutável e `load_settings()` lê:

- `HULI_ENV`
- `HULI_LOG_LEVEL`
- `HULI_DATA_DIR`

Nenhum segredo deve ser versionado. `.env.example` contém apenas nomes e valores seguros de exemplo.

## Logging

`configure_logging()` usa a biblioteca padrão do Python e cria linhas com campos previsíveis:

```text
timestamp level=INFO logger=huli message=...
```

A fundação não depende de bibliotecas externas de logging.

## Bootstrap

`huli/bootstrap.py` é o ponto oficial de composição de dependências concretas.

Ele cria:

1. Settings
2. logger
3. EventBus
4. SkillRegistry
5. FoundationSkill
6. Kernel

O Kernel permanece livre de criação de dependências.

## Regra

Esses componentes são infraestrutura da Fase 0. Eles não devem receber lógica de agenda, memória pessoal, IA, voz, visão ou automação residencial.
