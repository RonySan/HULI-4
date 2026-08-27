# Fase 4 staging — Personalidade e Conversação

Versão de staging: `4.0.0-alpha.10`.

## Objetivo

Dar à Huli uma personalidade consistente e previsível sem permitir que estilo altere fatos, segurança ou decisões de domínio.

## Arquitetura

```text
Kernel
  ↓
BrainDispatcher
  ↓
PersonalityEngine
  ├── resolve continuidade curta
  ├── seleciona modo conversacional
  └── publica conversation.mode.selected
  ↓
Intent / Skill Registry
  ↓
Skill
```

A personalidade não reescreve respostas factuais de memória, Knowledge Graph, Planner ou Agenda.

## Modos

- `casual`: conversa social e interações comuns;
- `professional`: projetos, tarefas, agenda, memória e conhecimento;
- `serious`: sinais explícitos de urgência ou gravidade;
- `risk`: operações classificadas como sensíveis, como esquecimento de memória e cancelamento.

## Continuidade social curta

Após uma interação `smalltalk`, expressões como `e você?`, `entendi`, `beleza`, `certo` e `ok` podem continuar a conversa sem depender de IA externa.

O contexto continua efêmero e é descartado ao fim da sessão.

## Evolução de linguagem natural da alpha.10

A validação manual da `alpha.8` mostrou que a base técnica passava nos testes,
mas frases naturais usadas no terminal ainda caíam no fallback. A `alpha.10`
transforma esses casos em regressões obrigatórias e acrescenta:

- consulta de data por variações como `que dia é hoje?`;
- consultas de agenda para hoje, amanhã e noite;
- `agenda` como atalho seguro para a agenda de hoje;
- criação de compromisso sem data explícita, usando a próxima ocorrência futura
  do horário informado e exibindo a data inferida na confirmação;
- normalização de `prioridade alto` para prioridade `alta`;
- registro controlado de informações declarativas sobre o projeto ativo;
- separação de tarefa embutida em uma atualização de projeto;
- sincronização da descrição do projeto com o Knowledge Graph;
- resumo factual das mensagens relevantes da sessão atual;
- reconhecimento natural do início de uma jornada de trabalho.

O resumo conversacional não atravessa sessões e não usa o histórico global, o
que preserva o isolamento. Memórias e tarefas continuam persistentes no SQLite.

## Identidade

- nome normal: `Huli`;
- sigla técnica: `HULI`;
- significado conhecido internamente: `Humano Único Leal Inteligente`;
- o significado só é expandido quando solicitado explicitamente;
- a Huli não deve pronunciar o nome letra por letra no uso normal.

## Segurança

- o modo conversacional nunca concede autorização;
- visitante continua sujeito à `SecurityPolicy`;
- mensagens de segurança não são estilizadas;
- respostas factuais não recebem adornos capazes de mudar seu sentido;
- OpenAI e Ollama continuam fora desta fase.

## Eventos

`conversation.mode.selected` registra modo, motivo, intent resolvida e se a mensagem foi tratada como continuidade curta.

## Validação

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\VALIDAR_FASE4.ps1
```

O validador cobre modos, continuidade social, identidade, contexto profissional,
data, agenda, tarefas, memória, conhecimento, resumo da sessão, estabilidade
factual e terminal/API usando o mesmo runtime.
