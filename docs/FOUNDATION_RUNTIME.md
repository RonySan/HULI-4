# Fundação de Runtime — Fase 0

Este documento registra a fundação executável da Huli 4.

## Fluxo principal

```text
Cliente local/API
      ↓
Autenticação
      ↓
SecurityPolicy
      ↓
Kernel
      ↓
SkillRegistry
      ↓
Skill compatível
      ↓
KernelResponse
      ↓
EventBus
      ↓
Persistência SQLite
```

## Kernel

O Kernel coordena entrada e saída. Ele conhece apenas contratos e não importa banco, API, autenticação, memória, IA ou Skills concretas.

## Skill Registry

O `SkillRegistry` implementa o contrato `KernelHandler`. A `FoundationSkill` existe somente para validar a arquitetura da Fase 0 e reconhece comandos técnicos como `ping`, `status`, `status huli` e `teste`.

## Eventos internos

O `EventBus` é síncrono e desacoplado. O Kernel publica:

- `kernel.request.received`
- `kernel.response.created`

O `RuntimeRecorder` assina esses eventos e persiste o histórico técnico sem criar dependência de SQLite dentro do Kernel.

## Persistência

A fundação usa SQLite em `HULI_DATA_DIR/huli.db`.

O banco possui migrações versionadas e, na Fase 0, mantém:

- `schema_migrations`
- `events`
- `interactions`
- `users`
- `sessions`

Esse armazenamento é infraestrutura. Ele ainda não é a Memory Engine inteligente prevista para a Fase 2.

## Autenticação

A Huli possui uma identidade proprietária local.

- na primeira execução via terminal, o proprietário é configurado;
- senhas são derivadas com `hashlib.scrypt` e salt aleatório;
- sessões usam tokens opacos aleatórios;
- apenas o hash SHA-256 do token fica persistido;
- sessões expiram e podem ser revogadas;
- o terminal revoga sua sessão ao encerrar.

A API expõe setup inicial somente enquanto nenhum usuário existir.

## SecurityPolicy

A política central define, nesta fase:

- tamanho mínimo de senha;
- limite máximo de caracteres por entrada;
- duração das sessões.

Ações de alto risco e permissões mais granulares serão adicionadas nas fases correspondentes, sem mover regras para o Kernel.

## API

A API usa FastAPI e fica, por padrão, vinculada a `127.0.0.1:8765`, evitando exposição externa acidental durante a Fase 0.

Rotas atuais:

```text
GET  /health
POST /v1/auth/setup
POST /v1/auth/login
POST /v1/auth/logout
GET  /v1/me
POST /v1/messages
```

`/health`, setup inicial e login possuem regras próprias. As rotas de identidade e mensagens exigem Bearer token válido.

Para iniciar localmente:

```powershell
python -m huli.api
```

A documentação interativa fica em `http://127.0.0.1:8765/docs` enquanto o servidor estiver em execução.

## Configuração

`Settings` é imutável e `load_settings()` lê:

- `HULI_ENV`
- `HULI_LOG_LEVEL`
- `HULI_DATA_DIR`
- `HULI_API_HOST`
- `HULI_API_PORT`
- `HULI_SESSION_HOURS`
- `HULI_MAX_INPUT_CHARS`

Nenhum segredo deve ser versionado. `.env.example` contém apenas valores seguros de exemplo.

## Logging

`configure_logging()` usa a biblioteca padrão do Python e cria linhas estruturadas e previsíveis.

## Bootstrap

`huli/bootstrap.py` é o único ponto oficial de composição das implementações concretas. Ele monta configuração, logging, banco, eventos, repositórios, Skills, autenticação, segurança e Kernel.

## Qualidade e CI

O pacote de desenvolvimento instala:

- pytest
- HTTPX para testes da API
- Ruff para lint/imports

O workflow `.github/workflows/ci.yml` executa em Python 3.11:

```text
ruff check .
pytest
```

## Regra arquitetural

A fundação não recebe lógica de agenda, memória pessoal, personalidade avançada, IA híbrida, voz, visão ou automação residencial. Esses recursos entram apenas nas fases previstas no roadmap.
