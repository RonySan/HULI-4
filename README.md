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

**Versão:** `4.0.0-alpha.2`  
**Fase atual:** Fase 0 — Fundação arquitetural  
**Status:** implementação concluída na branch `phase-0-foundation`; CI automatizado em Linux/Windows; aguardando somente validação manual final no Windows antes do merge.

## Fundação atual

```text
Cliente local / API
        ↓
Identidade e permissões
        ↓
SecurityPolicy
        ↓
Kernel
        ↓
SkillRegistry
        ↓
Skill
        ↓
KernelResponse
        ↓
EventBus
        ↓
SQLite
```

A Fase 0 inclui estrutura modular, Kernel, Skills, eventos, configuração, logging, persistência SQLite, autenticação, modo visitante, segurança, API FastAPI, testes, Ruff, CI e documentação.

## Instalação de desenvolvimento

Requer Python 3.11.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

## Validação completa da Fase 0 no Windows

Depois de atualizar a branch, execute:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\VALIDAR_FASE0.ps1
```

O script executa Ruff, Pytest e o validador ponta a ponta em banco temporário.

## Executar no terminal

```powershell
python main.py
```

Na primeira execução, Huli permite configurar o proprietário ou continuar como visitante. A senha do proprietário é **opcional**; se for utilizada, deve ter pelo menos 4 caracteres nesta fase.

Depois que existe um proprietário:

- o nome do proprietário entra como proprietário;
- se ele não configurou senha, nenhuma senha é pedida;
- se configurou senha, ela é solicitada;
- usuário vazio ou desconhecido entra como **visitante**;
- visitante só pode executar capacidades básicas não sensíveis permitidas pela `SecurityPolicy`.

## Executar API local

```powershell
python -m huli.api
```

Por padrão:

```text
http://127.0.0.1:8765
http://127.0.0.1:8765/docs
```

A API não deve ser exposta publicamente durante a Fase 0. Rotas protegidas continuam exigindo sessão de proprietário; visitante não recebe acesso protegido pela API.

## Roadmap e documentação

- [`docs/ROADMAP.md`](docs/ROADMAP.md)
- [`docs/FOUNDATION_RUNTIME.md`](docs/FOUNDATION_RUNTIME.md)
- [`docs/API_SECURITY.md`](docs/API_SECURITY.md)
- [`docs/ALPHA_2_VALIDATION.md`](docs/ALPHA_2_VALIDATION.md)
- [`docs/DEVELOPMENT_RULES.md`](docs/DEVELOPMENT_RULES.md)
- [`docs/PHASE_1_PLAN.md`](docs/PHASE_1_PLAN.md)

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
