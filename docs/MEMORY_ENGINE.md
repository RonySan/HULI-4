# Memory Engine 4.0 — Fase 2

## Objetivo

Dar à Huli memória persistente de longo prazo sem misturar lembrança registrada com inferência de IA.

## Princípio central

Memória é dado persistido, auditável e recuperável. OpenAI, Ollama ou qualquer modelo futuro podem ajudar a interpretar uma conversa, mas nunca podem fabricar uma lembrança que não exista no Memory Engine.

## Tipos de memória

- `episodic`: acontecimentos e experiências registradas;
- `semantic`: fatos estáveis;
- `person`: informações sobre pessoas;
- `project`: informações relacionadas a projetos;
- `preference`: preferências do proprietário;
- `temporal`: informações com contexto temporal.

## Origem

- `explicit`: o proprietário pediu para lembrar;
- `automatic`: veio de um `memory.candidate` aprovado pela política;
- `imported`: reservado para importações futuras;
- `system`: reservado para dados internos controlados.

## Sensibilidade

- `normal`: pode ser explícita ou, dentro das regras, automática;
- `sensitive`: só pode ser salva por ação explícita do proprietário;
- `secret`: nunca é armazenada.

Senhas, tokens, chaves de API e segredos semelhantes são recusados mesmo quando o proprietário pede explicitamente para lembrar.

## Isolamento

Toda memória possui `owner`. Consultas, listagens, acesso e esquecimento sempre incluem o proprietário. Um usuário não recebe memória pertencente a outro.

## Esquecimento

A Huli não apaga silenciosamente a linha do banco. A memória recebe `is_active = 0`, mantendo uma trilha técnica auditável. Memórias inativas não aparecem em recall ou listagem normal.

## Recuperação

A busca atual é determinística e local. O ranking usa:

1. igualdade normalizada;
2. ocorrência de frase;
3. interseção de tokens;
4. correspondência de assunto;
5. correspondência de projeto.

Não há embeddings, OpenAI ou Ollama nesta fase.

## Aprendizado automático controlado

O runtime escuta apenas eventos explícitos `memory.candidate`. Um candidato precisa:

- ter tipo permitido;
- não conter segredo;
- não ser sensível;
- atingir confiança mínima de `0.90`.

A conversa comum não é automaticamente despejada na memória.

## Eventos

A Memory Engine publica:

- `memory.created`
- `memory.updated`
- `memory.recalled`
- `memory.forgotten`
- `memory.candidate.accepted`
- `memory.candidate.rejected`

## Comandos iniciais

```text
lembre que eu prefiro café sem açúcar
o que você lembra sobre café?
minhas memórias
esqueça 12
```

O número usado em `esqueça` deve ser o ID realmente exibido pela Huli.

## Contexto de projeto

Se a sessão tem um projeto ativo na Fase 1, uma nova memória explícita herda esse projeto e é classificada como `project` quando nenhum tipo foi fornecido diretamente.

## Visitantes

Visitantes não podem salvar, consultar, listar ou esquecer memória privada.

## Limites da Fase 2

A Memory Engine não é Knowledge Graph. Relações entre entidades pertencem à Fase 3. Também não há personalidade, IA híbrida, voz ou controle do computador nesta fase.
