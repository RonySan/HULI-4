# Intent Engine + BrainDispatcher — Fase 1.1

## Objetivo

Classificar a intenção de uma mensagem sem executar ações prematuramente e tornar o roteamento consciente dessa classificação.

## Estado

O Intent Engine `alpha.4` foi validado localmente no Windows do usuário com 19 testes aprovados e o validador dedicado concluído com sucesso.

A `alpha.5` corrige a integração conversacional observada no teste manual: intenções reconhecidas não devem mais cair todas no mesmo fallback genérico.

## Saída do Intent Engine

`IntentMatch` contém `intent`, `confidence`, `normalized_text` e `metadata.matched_rule`.

## Intenções iniciais

- `system.status`
- `time.query`
- `agenda.query`
- `task.create`
- `smalltalk`
- `project.query`
- `unknown`

Essas intenções são vocabulário técnico interno. Elas não significam que Agenda, Planner, Small Talk ou Project Context já estejam implementados.

## BrainDispatcher

A partir da `4.0.0-alpha.5`, o Kernel usa `BrainDispatcher` como handler. O dispatcher classifica, publica `brain.intent.classified`, tenta resolver uma Skill e, quando a intenção é reconhecida mas a capacidade ainda não existe, devolve uma resposta específica de capacidade pendente.

Exemplos:

```text
que horas são?
→ time.query
→ informa que a capacidade de horário ainda não está ativa


o que temos pra fazer hoje?
→ agenda.query
→ informa que Agenda ainda não está ativa


oi huli, bom dia
→ smalltalk
→ informa que Small Talk ainda não está ativo


abrir o chrome
→ unknown
→ fallback controlado
```

## Regressão importante

`trocar o trocador de calor da piscina` deve permanecer `unknown`, sem disparar intenções por coincidência de substring.

## Limites desta etapa

- ainda não cria tarefas;
- ainda não consulta agenda real;
- ainda não responde horário real;
- ainda não mantém contexto;
- ainda não usa memória;
- ainda não chama IA externa.

Essas capacidades entram nos módulos correspondentes da Fase 1 e fases posteriores.
