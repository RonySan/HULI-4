# Intent Engine + BrainDispatcher — Fase 1.1

## Objetivo

Classificar a intenção de uma mensagem sem executar ações prematuramente e tornar o roteamento consciente dessa classificação.

## Entrada

Texto bruto do usuário.

## Saída do Intent Engine

`IntentMatch` com:

- `intent`;
- `confidence`;
- `normalized_text`;
- `metadata.matched_rule`.

## Intenções iniciais

- `system.status`
- `time.query`
- `agenda.query`
- `task.create`
- `smalltalk`
- `project.query`
- `unknown`

Essas intenções são vocabulário técnico interno. Elas não significam que Agenda, Planner, Small Talk ou Project Context já estejam implementados.

## Normalização

A normalização fica em `huli/brain/normalization.py` e é separada da classificação. Ela aplica `casefold`, remove acentos e pontuação e normaliza espaços.

## BrainDispatcher

A partir da `4.0.0-alpha.5`, o Kernel usa `BrainDispatcher` como handler. O dispatcher:

1. classifica a intenção;
2. publica `brain.intent.classified`;
3. tenta resolver uma Skill existente;
4. quando a intenção é reconhecida mas a capacidade ainda não foi implementada, devolve uma resposta específica de capacidade pendente;
5. para texto realmente desconhecido, usa fallback controlado.

Isso evita o comportamento anterior em que `que horas são?`, `minha agenda` e `oi Huli` recebiam exatamente o mesmo fallback, apesar de já terem sido classificados corretamente.

## Exemplos

```text
que horas são?
→ time.query
→ "Entendi que você quer saber o horário, mas essa capacidade ainda não está ativa."


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
