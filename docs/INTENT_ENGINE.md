# Intent Engine — Fase 1.1

## Objetivo

Classificar a intenção de uma mensagem sem executar ações e sem depender de OpenAI, Ollama ou qualquer serviço externo.

## Entrada

Texto bruto do usuário.

## Saída

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

A normalização fica em `huli/brain/normalization.py` e é separada da classificação. Ela:

1. aplica `casefold`;
2. remove acentos;
3. remove pontuação;
4. normaliza espaços.

## Regras

A classificação usa regras locais determinísticas e ordenadas. Uma frase que não corresponde de forma segura a nenhuma regra retorna `unknown` com confiança `0.0`.

Não existe fallback para IA nesta etapa.

## Integração com o runtime

`IntentObserver` escuta:

```text
kernel.request.received
```

classifica a mensagem e publica:

```text
brain.intent.classified
```

com `request_id`, intenção, confiança, texto normalizado e regra correspondente.

O Kernel não importa nem conhece o Intent Engine.

## Regressão importante

Frases como:

```text
trocar o trocador de calor da piscina
```

não podem disparar intenção de horário ou qualquer outra por coincidência de substring.

## Limites desta etapa

- não executa ações;
- não cria tarefas;
- não consulta agenda;
- não mantém contexto;
- não usa memória;
- não chama IA externa;
- ainda não substitui o roteamento das Skills.

A integração de intenção + contexto + roteamento será evoluída ao longo da Fase 1 sem adicionar regras de domínio ao Kernel.

## Critério de aceite

Frases equivalentes devem chegar à mesma intenção, desconhecidos devem permanecer controlados e toda requisição do Kernel deve gerar `brain.intent.classified` sem alterar a responsabilidade do Kernel.
