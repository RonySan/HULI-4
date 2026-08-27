# API e Segurança — Fase 0

## Objetivo

A API da Fase 0 existe para validar a futura arquitetura PC + celular + servidor. Ela ainda não é um serviço de produção público.

## Endereço padrão

```text
127.0.0.1:8765
```

O bind local reduz exposição acidental enquanto autenticação e políticas ainda estão na fundação.

## Rotas

- `GET /health`: pública, apenas estado técnico.
- `POST /v1/auth/setup`: pública somente enquanto não existe proprietário.
- `POST /v1/auth/login`: valida credenciais e cria sessão.
- `GET /v1/me`: protegida.
- `POST /v1/auth/logout`: protegida e revoga a sessão.
- `POST /v1/messages`: protegida e encaminha texto ao Kernel.

## Proprietário e senha opcional

A senha do proprietário é opcional na execução local. Se o proprietário escolher uma senha nova, ela deve ter pelo menos 8 caracteres. Senhas curtas criadas em versões anteriores continuam permitindo login para que o proprietário migre os dados e faça a troca com segurança. Se deixar a senha vazia, o nome do proprietário é suficiente para o acesso local, mas o diário permanece bloqueado.

Quando existe senha, ela usa `hashlib.scrypt` com salt aleatório. Mesmo quando a senha é vazia, o banco armazena somente o hash derivado e o salt, nunca a senha original.

A API continua exigindo uma sessão de proprietário para rotas protegidas. Um proprietário configurado sem senha pode autenticar enviando senha vazia enquanto a API estiver restrita ao ambiente local da Fase 0.

## Modo visitante

A interface local permite acesso como visitante quando:

- o campo de usuário é deixado vazio; ou
- o nome informado não corresponde ao proprietário configurado.

O visitante não recebe token de proprietário e só pode usar comandos básicos e não sensíveis da `FoundationSkill`, como `ping` e `status`. Memória pessoal, configurações, integrações, automações e ações sensíveis devem exigir proprietário quando forem implementadas.

A API **não** converte usuário desconhecido em proprietário nem oferece acesso anônimo às rotas protegidas.

## Sessões

O cliente proprietário recebe um token opaco aleatório. O SQLite armazena somente SHA-256 desse token. Sessões possuem expiração e revogação.

## Cofre do diário — Fase 4.2

Um login com senha válida abre a chave do diário apenas na memória do processo.
O logout bloqueia a chave, e a inatividade volta a bloqueá-la mesmo quando o
token HTTP ainda não expirou. Nesse caso, o cliente deve autenticar novamente.

O retorno de `POST /v1/auth/login` informa se houve migração de entradas antigas
e o caminho local do backup criado. O conteúdo do diário nunca aparece nessa
resposta. A API não possui rota de exportação ou restauração nesta fase; essas
operações permanecem locais e exigem confirmação pelo terminal.

## Limites

`SecurityPolicy` concentra senha opcional, tamanho máximo de entrada, duração de sessão e comandos permitidos ao visitante.

## Produção futura

Antes de expor a API para internet serão necessários, nas fases correspondentes:

- HTTPS/TLS;
- reverse proxy;
- rate limiting;
- política de origem/CORS;
- auditoria e alertas;
- rotação/revogação administrativa;
- permissões por dispositivo/ação;
- proteção específica para comandos de alto risco;
- revisão da política de proprietário sem senha para acesso remoto.
