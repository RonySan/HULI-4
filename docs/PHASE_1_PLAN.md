# Fase 1 — Cérebro básico

A Fase 1 começa somente depois de a Fase 0 ser validada no Windows, mergeada em `main` e encerrada oficialmente.

## Objetivo

Fazer a Huli deixar de ser apenas infraestrutura e começar a compreender solicitações básicas, manter contexto curto e operar capacidades pessoais essenciais sem depender de IA externa quando regras locais forem suficientes.

## Ordem oficial

1. **Intent Engine**
2. **Context Engine**
3. **Planner**
4. **Agenda**
5. **Daily Summary**
6. **Small Talk**
7. **Project Context**
8. **Integração final da Fase 1**

A ordem não deve ser alterada por novas ideias. Novas capacidades entram no módulo/fase correspondente.

---

## 1. Intent Engine

Responsabilidade: classificar a intenção de uma mensagem sem executar ações.

Entrada:

```text
texto do usuário
```

Saída mínima:

```text
intent
confidence
entities/metadados básicos
```

Requisitos:

- normalização de texto separada da classificação;
- regras locais determinísticas para intents fundamentais;
- nenhuma chamada à OpenAI/Ollama nesta etapa;
- desconhecido deve virar `conversation`/`unknown` controlado, nunca invenção;
- testes para variações naturais e erros comuns de digitação.

Critério de aceite: frases equivalentes chegam à mesma intenção sem colocar regras de domínio no Kernel.

---

## 2. Context Engine

Responsabilidade: manter contexto curto da sessão atual.

Requisitos:

- histórico limitado e estruturado;
- referência à última intenção e último assunto;
- contexto separado da memória de longo prazo da Fase 2;
- sem persistir fatos pessoais automaticamente;
- suporte a `session_id` para futura API multi-dispositivo.

Critério de aceite: uma segunda mensagem pode usar contexto da anterior sem transformar o Kernel em armazenamento de conversa.

---

## 3. Planner

Responsabilidade: tarefas pessoais e de projetos.

Requisitos mínimos:

- criar tarefa;
- listar pendentes;
- concluir tarefa;
- prioridade;
- vínculo opcional com projeto;
- linguagem natural básica;
- persistência por repositório próprio;
- eventos de criação/conclusão.

Critério de aceite: adicionar, consultar e concluir tarefas pelo mesmo fluxo usado por terminal e API.

---

## 4. Agenda

Responsabilidade: compromissos com data/hora.

Requisitos mínimos:

- criar compromisso;
- listar próximos;
- cancelar compromisso;
- validar data/hora;
- persistência própria;
- sem Google Calendar nesta fase.

Critério de aceite: agenda local funciona de forma confiável antes de qualquer integração externa.

---

## 5. Daily Summary

Responsabilidade: produzir um resumo objetivo do dia usando dados reais.

Fontes permitidas nesta fase:

- tarefas;
- compromissos;
- contexto local relevante.

Critério de aceite: responder o que existe para hoje sem inventar itens inexistentes.

---

## 6. Small Talk

Responsabilidade: conversação básica local e natural.

Requisitos:

- saudações;
- agradecimentos;
- despedidas;
- respostas curtas e variadas;
- identidade exibida como `Huli`;
- nunca recitar automaticamente o significado de HULI.

Critério de aceite: conversa social básica não precisa de IA externa.

---

## 7. Project Context

Responsabilidade: identificar e manter o projeto ativo na sessão.

Requisitos:

- projeto explícito na frase;
- último projeto ativo da sessão;
- tarefas podem herdar projeto quando o contexto for inequívoco;
- não confundir Project Context com Project Memory da Fase 2.

Critério de aceite: `adiciona revisar o banco` pode ser vinculado ao projeto ativo quando o contexto comprovar qual é.

---

## 8. Integração final

Fluxo esperado:

```text
entrada
↓
Kernel
↓
Intent Engine
↓
Context Engine
↓
Skill Registry
↓
Skill especializada
↓
serviço/repositório de domínio
↓
EventBus
↓
persistência
↓
resposta
```

## Regras arquiteturais

- Kernel coordena; não executa regras de tarefas, agenda ou conversa.
- Intent Engine classifica; não executa ações.
- Context Engine mantém contexto curto; não é Memory Engine.
- Skills interpretam e delegam para serviços/repositórios de domínio.
- Persistência continua atrás de repositórios.
- IA externa não é requisito da Fase 1.
- Terminal e API devem usar o mesmo runtime.

## Critério final da Fase 1

A Fase 1 termina quando a Huli consegue, com testes automatizados e sem IA externa obrigatória:

1. entender intenções fundamentais;
2. manter contexto curto;
3. criar/listar/concluir tarefas;
4. criar/listar/cancelar compromissos;
5. resumir o dia;
6. conversar socialmente de forma básica;
7. manter contexto de projeto;
8. oferecer o mesmo comportamento por terminal e API.
