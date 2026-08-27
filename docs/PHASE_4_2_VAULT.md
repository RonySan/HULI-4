# Fase 4.2 staging — Cofre Pessoal Seguro

Versão de staging: `4.0.0-alpha.12`.

## Objetivo

Proteger o diário da Huli em repouso sem simular segurança com uma chave salva
ao lado do banco. A evolução preserva todas as funções da alpha.11 e acrescenta
criptografia autenticada, ciclo de bloqueio, migração segura e recuperação por
backup portátil.

## O que fica cifrado

| Dado | Proteção no SQLite |
|---|---|
| Conteúdo da entrada | AES-256-GCM |
| Texto usado na pesquisa | AES-256-GCM |
| Humor declarado | AES-256-GCM |
| Etiquetas | AES-256-GCM |
| Palavras pesquisáveis | Índice cego HMAC-SHA-256 |
| Proprietário, data e horários | Metadados visíveis |
| Sensibilidade e estado ativo/lixeira | Metadados visíveis |

Cada campo recebe nonce aleatório e AAD ligada ao proprietário, identificador
criptográfico da entrada e nome do campo. Qualquer alteração no ciphertext é
recusada antes que o conteúdo seja exibido.

## Chaves

1. A Huli gera uma chave mestra aleatória de 256 bits por proprietário.
2. Uma chave de envelope é derivada da senha com `scrypt`, salt aleatório e
   parâmetros versionados.
3. A chave mestra é cifrada com AES-256-GCM; a senha e a chave aberta nunca são
   gravadas.
4. No Windows, o envelope cifrado recebe uma segunda camada DPAPI vinculada à
   conta atual do sistema.
5. Em outros sistemas, o envelope permanece protegido pela senha. Ao levar um
   cofre `password-only` para o Windows, a Huli acrescenta DPAPI automaticamente.

Um cofre protegido por DPAPI não deve ser copiado como método de migração para
outra conta ou sistema. Para isso, use o backup portátil `.hulibak`.

## Migração da alpha.11

Na primeira autenticação com senha:

1. a Huli localiza entradas ainda legíveis;
2. cria um backup `.hulibak` cifrado pela senha atual;
3. cifra todas as entradas em uma única transação;
4. substitui os campos antigos por valores vazios;
5. cria índices cegos de pesquisa;
6. executa checkpoint, truncamento do WAL e `VACUUM` com `secure_delete`;
7. marca a limpeza como concluída.

Se o backup não puder ser criado, a migração não começa. Se a transação falhar,
as entradas antigas permanecem intactas. Se a limpeza final falhar, o cofre fica
bloqueado e tenta concluí-la novamente no próximo login.

O caminho do backup aparece no terminal e na resposta autenticada de login da
API. Ele normalmente fica em `data/backups/`.

## Bloqueio

- login válido abre a chave somente em memória;
- logout e encerramento do terminal removem a chave do cache;
- inatividade bloqueia o diário após 15 minutos por padrão;
- `HULI_JOURNAL_LOCK_MINUTES` permite configurar de 1 a 1440 minutos;
- um token HTTP ainda válido não ignora o bloqueio: é necessário entrar de novo.

A limpeza de memória é feita em melhor esforço. Python e bibliotecas nativas
podem manter cópias transitórias durante uma operação criptográfica; por isso, a
proteção da conta do sistema e do disco continua necessária.

## Backup e restauração

```powershell
python tools/backup_journal.py
python tools/restore_journal.py
```

O backup usa AES-256-GCM e uma derivação scrypt própria, independente do cofre e
do sistema operacional. A restauração:

- valida senha, proprietário, formato e integridade antes de alterar o banco;
- recusa substituição sem a confirmação literal `RESTAURAR`;
- cria outro backup criptografado do diário atual antes da troca;
- restaura conteúdo e lixeira em uma transação, com novos IDs seguros.

Backups não mudam de senha automaticamente. Um arquivo criado com uma senha
antiga continuará exigindo essa senha, mesmo depois que a senha atual da conta
for alterada.

## Troca de senha

`python tools/set_local_password.py` valida a senha atual, reenvelopa a mesma
chave mestra com a nova senha e revoga todas as sessões existentes. As entradas
não precisam ser decifradas e gravadas novamente.

A senha só pode ser removida quando o diário não possui entradas. Essa regra
impede que um cofre real fique sem material seguro para abertura.

## Limites honestos

- metadados operacionais continuam visíveis;
- o nome e a quantidade aproximada de entradas não são ocultados;
- índices cegos escondem as palavras, mas revelam repetições de um mesmo token
  dentro do mesmo cofre;
- não existe recuperação silenciosa de senha;
- sem a senha correta e sem backup utilizável, os registros são irrecuperáveis;
- esta fase não adiciona inferência emocional, diagnóstico, memória automática
  ou envio do diário para IA externa;
- BitLocker, senha forte do Windows e backups externos continuam recomendados.

## Validação

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\VALIDAR_FASE4_2.ps1
```

O script executa Ruff, todos os testes e as regressões das Fases 0 a 4.2.
