# Fase 4.1 staging — Diário Pessoal Privado

Versão de staging: `4.0.0-alpha.11`.

> Documento histórico. A limitação de texto em repouso descrita abaixo foi
> corrigida pela Fase 4.2 na `4.0.0-alpha.12`.

## Objetivo

Permitir que o proprietário use a Huli como diário pessoal persistente sem
misturar automaticamente relatos íntimos com memória, conhecimento, tarefas ou
contexto comum de conversa.

## Capacidades

- registrar uma entrada de hoje ou de ontem;
- registrar data explícita no formato `DD/MM/AAAA`;
- adicionar humor declarado e até dez etiquetas;
- consultar hoje, ontem, uma data ou as entradas mais recentes;
- pesquisar por palavras presentes no texto, humor ou etiquetas;
- editar uma entrada pelo número;
- apagar logicamente uma entrada pelo número;
- consultar a lixeira e restaurar uma entrada pelo número;
- manter os registros após reiniciar o runtime;
- usar a mesma capacidade pelo terminal e pela API autenticada.

## Exemplos

```text
diário: hoje foi um dia importante
anote no meu diário de ontem: visitei minha família
diário: finalizei uma etapa | humor: feliz | tags: trabalho, Huli
meu diário de hoje
o que escrevi ontem no diário?
procure no meu diário por família
edite a entrada #1 do diário: texto corrigido
apague a entrada #1 do diário
lixeira do meu diário
restaure a entrada #1 do diário
como uso meu diário?
```

Humor e etiquetas são opcionais e somente são registrados quando declarados.
A Huli não tenta diagnosticar nem inferir o estado emocional do proprietário.

## Arquitetura

```text
Intent Engine
  ↓
JournalSkill
  ↓
JournalService
  ├── JournalPolicy
  ├── EventBus sem conteúdo
  └── JournalRepository
        ↓
SQLite schema 7
```

O diário possui tabela e domínio próprios. Nenhuma entrada publica
`memory.candidate`, cria entidade no Knowledge Graph ou vira tarefa.

## Privacidade

- somente `role=owner` com usuário identificado e senha configurada pode acessar a Skill;
- toda consulta inclui o `owner`, impedindo cruzamento entre usuários;
- visitante não pode registrar, listar, pesquisar, editar ou apagar;
- o conteúdo é substituído por `[conteúdo privado do diário]` antes de persistir
  eventos e interações operacionais;
- o contexto curto recebe somente a marca de redação;
- o resumo da conversa ignora intents `journal.*`;
- eventos do domínio registram apenas ID, proprietário, data, sensibilidade e
  quantidade de etiquetas;
- senhas, tokens, chaves de API e outros segredos são recusados;
- exclusão é lógica, com lixeira e restauração, para evitar perda acidental.

## Limite conhecido da alpha.11

O conteúdo está isolado no aplicativo, mas ainda é armazenado em texto no banco
SQLite. A criptografia em repouso exigirá um cofre de chaves adequado e não será
simulada com uma chave ao lado do próprio banco. Até essa evolução:

- use senha na conta proprietária da Huli;
- proteja a conta do Windows;
- mantenha BitLocker habilitado no disco;
- não registre credenciais no diário;
- não envie `data/huli.db` para o Git.

Se o proprietário foi criado sem senha, configure uma antes de usar o diário:

```powershell
python tools/set_local_password.py
```

## Validação

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\VALIDAR_FASE4_1.ps1
```

O validador executa todas as regressões anteriores e depois verifica o diário em
persistência, linguagem natural, API, isolamento, redação e política de segredo.
