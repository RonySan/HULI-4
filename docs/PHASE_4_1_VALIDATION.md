# Validação da Fase 4.1 — alpha.11

- Data: 2026-08-27
- Branch: `phase-4-journal-staging`
- Versão: `4.0.0-alpha.11`
- Python local: `3.11.15`

## Resultado automatizado

```text
Ruff: aprovado
Pytest: 132 aprovados, 0 falhas, 0 avisos
Fase 0: aprovada
Intent Engine: aprovado
Fase 1: aprovada
Fase 2 — Memory Engine: aprovada
Fase 3 — Knowledge Graph staging: aprovada
Fase 4 — Personalidade e Conversação staging: aprovada
Fase 4.1 — Diário Pessoal Privado: aprovada
```

## Casos novos cobertos

- registro natural com `diário: ...`;
- registro retroativo de ontem;
- humor declarado e etiquetas opcionais;
- consulta de hoje, ontem e entradas recentes;
- pesquisa textual sem acentos e por etiquetas;
- edição explícita por ID;
- exclusão lógica explícita por ID;
- lixeira privada e restauração por ID;
- persistência depois de reiniciar o runtime;
- funcionamento pelo terminal e pela API autenticada;
- recusa de acesso para visitante ou identidade incompleta;
- bloqueio do diário quando a conta proprietária não possui senha;
- isolamento entre proprietários;
- recusa de senhas, tokens e chaves;
- ausência de criação automática de memória, conhecimento ou tarefa;
- redação do conteúdo em eventos, interações técnicas e contexto curto;
- exclusão do diário nos resumos comuns da conversa;
- modos de personalidade `private` e `risk`.

## Persistência

O schema SQLite avançou para a versão 7 com a tabela `journal_entries`. Cada
consulta exige o proprietário, e exclusões mantêm o registro inativo durante a
staging para permitir auditoria e evitar perda acidental.

## Segurança verificada

O conteúdo do diário aparece somente na resposta autenticada e na tabela do
domínio. Eventos e histórico técnico recebem a marca
`[conteúdo privado do diário]`. Eventos `journal.*` contêm somente metadados.

## Limite conhecido

O SQLite ainda não possui criptografia própria em repouso. Isso está documentado
sem falsa promessa de segurança; a recomendação atual é conta do Windows
protegida, BitLocker ativo e nenhuma credencial registrada no diário.
