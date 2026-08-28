# Fase 4 — Personalidade e Conversação

## Objetivo

A Fase 4 adiciona comportamento conversacional consistente à Huli sem permitir que estilo altere fatos, memória, conhecimento ou regras de segurança.

## Arquitetura

```text
Kernel
  ↓
BrainDispatcher
  ├─ IntentEngine
  ├─ ContextEngine        → assunto/projeto da sessão
  └─ ConversationEngine   → modo/tom/sinal da sessão
          ↓
      SkillRegistry
          ↓
      resposta factual/social
```

O `ContextEngine` e o `ConversationEngine` são deliberadamente separados.

- Contexto responde **sobre o que estamos falando**.
- Conversação responde **como a Huli deve falar naquele momento**.

## Modos

### Automático
A Huli seleciona o modo conforme intenção, texto e sinais da sessão.

### Casual
Tom mais leve e natural. Humor controlado pode aparecer em Small Talk.

### Profissional
Tom objetivo para projetos, tarefas, agenda, sistemas, clientes e operações de trabalho.

### Sério
Ativado por frustração/urgência ou manualmente. Humor fica desativado.

### Risco
Ativado automaticamente por conteúdo sensível/de risco ou manualmente. Segurança e confirmação têm prioridade; humor fica desativado.

## Comandos

```text
modo casual
modo profissional
modo sério
modo risco
modo automático
qual o modo atual
```

O modo manual persiste somente na sessão atual. `modo automático` remove o override.

Uma solicitação de risco pode temporariamente prevalecer sobre um modo manual casual/profissional. Depois, o modo manual volta a valer.

## Sinais conversacionais

O motor detecta localmente:

- `neutral`
- `positive`
- `gratitude`
- `frustration`
- `urgency`
- `risk`

Esses sinais não são diagnósticos emocionais. São apenas indicadores de estilo para a conversa atual.

## Identidade

O nome comum é **Huli**.

A expansão `Humano Único Leal Inteligente` somente é apresentada quando o usuário pergunta explicitamente o significado. A Huli não pronuncia o nome como letras separadas no uso normal.

## Segurança

Personalidade nunca pode:

- alterar fatos da Memory Engine;
- alterar relações do Knowledge Graph;
- inventar dados para soar mais natural;
- liberar permissões de visitante;
- adicionar humor em modo sério/risco;
- executar ação que não possua Skill/capacidade segura.

Visitantes podem usar Small Talk, horário, status e controlar o modo da própria sessão, mas continuam sem acesso a memória, conhecimento privado, agenda ou tarefas pessoais.

## API

`POST /v1/messages` agora também devolve:

```json
{
  "conversation_mode": "professional",
  "conversation_signal": "neutral",
  "humor_allowed": true
}
```

O estado é separado por `session_id`.

## Eventos

O `BrainDispatcher` publica `brain.conversation.updated` com:

- `session_id`
- `mode`
- `override`
- `signal`
- `humor_allowed`
- `turn_count`

## Gate

A Fase 4 só pode ser promovida para `main` após:

1. Ruff aprovado;
2. Pytest completo aprovado;
3. regressões das Fases 0 a 3 aprovadas;
4. `tools/validate_phase4.py` aprovado;
5. CI Windows e Ubuntu aprovados.
