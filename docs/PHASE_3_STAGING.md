# Fase 3 staging — Personal Knowledge Graph

## Estado

Esta implementação é uma **staging antecipada** da Fase 3. Ela depende da branch `phase-2-memory` e não substitui o gate oficial do roadmap.

A Fase 3 só se torna oficial depois de:

1. validação local da Fase 2;
2. merge do PR #6 em `main`;
3. fechamento da Issue #5;
4. promoção/rebase desta staging para a branch oficial da Fase 3.

## Objetivo

Transformar parte da memória persistida em conhecimento pessoal estruturado e consultável, preservando a memória original como fonte.

## Arquitetura

```text
Memory Engine
    ↓ eventos memory.created / memory.updated / memory.forgotten
MemoryKnowledgeSynchronizer
    ↓ somente padrões determinísticos suportados
KnowledgeService
    ↓
KnowledgeRepository
    ↓
SQLite schema 6
    ├── knowledge_entities
    ├── knowledge_entity_sources
    ├── knowledge_aliases
    ├── knowledge_relations
    └── knowledge_facts
```

Consultas:

```text
mensagem
  ↓
Intent Engine
  ↓
BrainDispatcher
  ↓
KnowledgeSkill
  ↓
KnowledgeService
  ↓
KnowledgeRepository
```

## Entidades

Tipos atuais:

- `person`
- `project`
- `company`
- `client`
- `system`
- `equipment`
- `place`
- `concept`

Uma entidade possui proprietário, nome canônico, nome normalizado, tipo, sensibilidade, datas e estado ativo.

## Aliases

Aliases permitem que nomes alternativos apontem para a mesma entidade sem duplicar conhecimento.

Exemplo:

```text
Impulso Digital
└── alias: Impulso
```

## Relações

Relações são direcionais e carregam proveniência, confiança e sensibilidade.

Predicados iniciais extraídos deterministicamente de memórias:

- `desenvolvido_por`
- `hospedado_em`
- `depende_de`
- `pertence_a`
- `cliente_de`

Exemplo:

```text
Medynx --desenvolvido_por--> Impulso Digital
Medynx --depende_de---------> MySQL
Medynx --hospedado_em-------> servidor Casa
```

## Fatos

Fatos são valores estruturados ligados a uma entidade.

Exemplos iniciais suportados pelo sincronizador:

- `status`
- `porta`

Fatos também podem ser criados explicitamente pelo serviço interno.

## Proveniência

Conhecimento derivado de memória mantém `source_memory_id`.

Quando a memória-fonte é esquecida:

1. relações derivadas daquela memória são desativadas;
2. fatos derivados daquela memória são desativados;
3. aliases derivados são desativados;
4. a ligação entidade ↔ memória é removida;
5. entidades sem outra fonte e sem origem manual podem ser desativadas.

Isso evita que a Huli continue afirmando conhecimento cuja única fonte foi esquecida.

## Política de não-alucinação

A staging não usa OpenAI ou Ollama para inventar entidades, relações ou fatos.

A sincronização automática só cria estruturas quando uma regra determinística reconhece explicitamente a informação da memória.

Se a relação não estiver registrada, a `KnowledgeSkill` responde que não encontrou conhecimento suficiente.

## Separação Memory x Knowledge

`Memory Engine` responde perguntas como:

```text
o que você lembra sobre Medynx?
```

`Knowledge Graph` responde perguntas como:

```text
o que você sabe sobre Medynx?
quem desenvolve Medynx?
qual servidor hospeda Medynx?
do que Medynx depende?
```

Memória é a evidência persistida. O grafo é uma visão estruturada apoiada por essa evidência.

## Segurança

- conhecimento é isolado por proprietário;
- visitante não consulta conhecimento pessoal;
- sensibilidade é herdada da memória-fonte;
- memórias `secret` não entram no grafo;
- esquecimento remove conhecimento derivado da fonte;
- o Kernel não conhece detalhes do grafo.

## Validação

Linux e Windows usam a mesma cadeia:

```text
Ruff
→ Pytest
→ Fase 0
→ Intent Engine
→ Fase 1
→ Fase 2
→ Fase 3 staging
```

Validação Windows local:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\VALIDAR_FASE3_STAGING.ps1
```

Resultado esperado:

```text
FASE 3 STAGING APROVADA NESTE COMPUTADOR
```
