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

## Credenciais

Senhas usam `hashlib.scrypt` com salt aleatório. O banco não armazena a senha original.

## Sessões

O cliente recebe um token opaco aleatório. O SQLite armazena somente SHA-256 desse token. Sessões possuem expiração e revogação.

## Limites

`SecurityPolicy` concentra limites mínimos de senha, tamanho máximo de entrada e duração de sessão.

## Produção futura

Antes de expor a API para internet serão necessários, nas fases correspondentes:

- HTTPS/TLS;
- reverse proxy;
- rate limiting;
- política de origem/CORS;
- auditoria e alertas;
- rotação/revogação administrativa;
- permissões por dispositivo/ação;
- proteção específica para comandos de alto risco.
