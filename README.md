# Huli 4

Huli é uma assistente pessoal de inteligência artificial local-first, projetada para acompanhar o usuário de forma contínua entre computador, celular e servidor.

O objetivo do projeto não é criar apenas uma agenda ou um chatbot. Huli deverá evoluir como uma plataforma pessoal de IA com memória de longo prazo, contexto, Skills, agentes, voz, visão, integrações e automação segura.

## Identidade

- Nome falado e exibido normalmente: **Huli**.
- A sigla técnica é **HULI**.
- Significado conhecido internamente: **Humano Único Leal Inteligente**.
- Huli não repete o significado da sigla ao se apresentar ou em respostas comuns.
- O significado só é explicado quando solicitado ou necessário em contexto técnico/documental.
- O nome é pronunciado **Huli**, não letra por letra.

## Princípio de desenvolvimento

> Só avançamos de fase quando a anterior estiver funcionando, testada, documentada e salva no Git.

A arquitetura é construída desde o início pensando em **PC + celular + servidor**, ainda que as primeiras versões sejam executadas apenas no computador.

## Estado atual

- **Versão:** `4.0.0-alpha.10`
- **Fase atual:** Fase 4 staging — Personalidade e Conversação
- **Módulo atual:** linguagem natural determinística e continuidade da sessão
- **Branch de desenvolvimento:** `phase-4-personality-staging`

As regressões das Fases 0 a 3 são executadas antes da validação da Fase 4. A
`main` continua protegida; código de staging só deve ser integrado depois da
validação local do usuário e do CI.

## Fluxo atual

```text
Cliente local / API
        ↓
Identidade e permissões
        ↓
SecurityPolicy
        ↓
Kernel
        ↓
kernel.request.received
        ↓
Intent Engine + Context Engine
        ↓
Personality Engine
        ↓
SkillRegistry
        ↓
Skill
  ├── tarefas e agenda
  ├── memória de longo prazo
  ├── conhecimento estruturado
  └── continuidade da conversa
        ↓
KernelResponse
        ↓
EventBus
        ↓
SQLite
```

O cérebro local classifica intenções, mantém contexto curto e executa Skills de
forma determinística. Personalidade nunca altera fatos, permissões ou decisões
de domínio. OpenAI e Ollama continuam fora desta fase.

## Capacidades atuais

- `system.status`
- `time.query`
- `date.query`
- `agenda.query`
- `agenda.create`
- `agenda.cancel`
- `task.create`
- `task.list`
- `task.complete`
- `smalltalk`
- `conversation.recap`
- `project.set`
- `project.note`
- `project.query`
- `memory.remember`
- `memory.recall`
- `memory.list`
- `memory.forget`
- `knowledge.describe`
- `knowledge.relation`
- `unknown`

A `alpha.10` também entende variações naturais verificadas no uso real, como
“que dia é hoje?”, “como está nossa agenda essa noite?”, “agenda pra mim jantar
às 22 horas” e “o que conversamos mais cedo?”.

## Instalação de desenvolvimento

Requer Python 3.11.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

## Qualidade

```powershell
python -m ruff check .
python -m pytest
powershell -ExecutionPolicy Bypass -File .\scripts\VALIDAR_FASE4.ps1
```

O CI executa em Linux e Windows nas branches `phase-*` e em `main`.

## Executar no terminal

```powershell
python main.py
```

A senha do proprietário é opcional. Usuários desconhecidos podem entrar em modo visitante com permissões limitadas.

## Executar API local

```powershell
python -m huli.api
```

Por padrão:

```text
http://127.0.0.1:8765
http://127.0.0.1:8765/docs
```

A API ainda não deve ser exposta diretamente à internet.

## Roadmap e documentação

- [`docs/ROADMAP.md`](docs/ROADMAP.md)
- [`docs/PHASE_1_PLAN.md`](docs/PHASE_1_PLAN.md)
- [`docs/PHASE_2_PLAN.md`](docs/PHASE_2_PLAN.md)
- [`docs/PHASE_3_STAGING.md`](docs/PHASE_3_STAGING.md)
- [`docs/PHASE_4_STAGING.md`](docs/PHASE_4_STAGING.md)
- [`docs/PHASE_4_VALIDATION.md`](docs/PHASE_4_VALIDATION.md)
- [`docs/INTENT_ENGINE.md`](docs/INTENT_ENGINE.md)
- [`docs/FOUNDATION_RUNTIME.md`](docs/FOUNDATION_RUNTIME.md)
- [`docs/API_SECURITY.md`](docs/API_SECURITY.md)
- [`docs/PHASE_0_VALIDATION.md`](docs/PHASE_0_VALIDATION.md)
- [`docs/DEVELOPMENT_RULES.md`](docs/DEVELOPMENT_RULES.md)

## Estrutura oficial

```text
HULI-4/
├── huli/
│   ├── core/
│   ├── brain/
│   ├── memory/
│   ├── skills/
│   ├── agents/
│   ├── api/
│   ├── security/
│   ├── integrations/
│   ├── voice/
│   ├── vision/
│   ├── clients/
│   └── infrastructure/
├── tests/
├── tools/
├── scripts/
├── docs/
├── main.py
├── pyproject.toml
├── .env.example
└── .gitignore
```

## Segurança

Dados sensíveis, tokens, bancos locais, arquivos `.env`, chaves e credenciais nunca devem ser versionados.

## Regra arquitetural

Novas ideias não alteram arbitrariamente a arquitetura ou a ordem do projeto. Elas devem ser encaixadas na fase correspondente do roadmap.
