# Validação da Fase 4 — alpha.10

- Data: 2026-08-27
- Branch: `phase-4-personality-staging`
- Versão: `4.0.0-alpha.10`
- Python local: `3.11.15`

## Motivo da evolução

A validação manual da `alpha.8` revelou frases naturais que ainda caíam no
fallback, embora a suíte técnica anterior estivesse verde. Todos os casos
observados foram reproduzidos antes da correção e transformados em testes de
regressão.

## Resultado automatizado

```text
Ruff: aprovado
Pytest: 109 aprovados, 0 falhas, 0 avisos
Fase 0: aprovada
Intent Engine: aprovado
Fase 1: aprovada
Fase 2 — Memory Engine: aprovada
Fase 3 — Knowledge Graph staging: aprovada
Fase 4 — Personalidade e Conversação staging: aprovada
```

## Casos reais agora cobertos

- `ok, então vamos começar os trabalhos de hoje`;
- `que dia é hoje?`;
- `como está a agenda pra hoje?`;
- `como está nossa agenda essa noite?`;
- `agenda`;
- `temos compromissos hoje à noite?`;
- `agenda pra mim jantar às 22 horas com a Gisele`;
- atualização natural do projeto Medynx com memória e tarefa na mesma frase;
- `prioridade alto`, normalizada para prioridade alta;
- `o que conversamos mais cedo?`.

## Persistência e segurança

- tarefas, compromissos e memórias foram recriados em um segundo runtime usando
  o mesmo banco SQLite;
- o resumo da conversa usa somente o contexto efêmero e isolado da sessão;
- informações naturais de projeto passam pela política da Memory Engine;
- conteúdos classificados como segredo continuam bloqueados;
- visitante pode consultar data, mas não memória, conhecimento ou resumo privado;
- nenhuma credencial foi adicionada ao repositório.

## Dependência de testes

O adaptador legado `httpx` foi substituído por `httpx2`, conforme exigido pelo
`TestClient` da versão atual do Starlette. A suíte agora trata o aviso de
descontinuação como erro para impedir regressão silenciosa.
