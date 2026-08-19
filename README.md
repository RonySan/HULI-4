# Huli 4

Huli é uma assistente pessoal de inteligência artificial local-first, projetada para acompanhar o usuário de forma contínua entre computador, celular e servidor.

O objetivo do projeto não é criar apenas uma agenda ou um chatbot. Huli deverá evoluir como uma plataforma pessoal de IA com memória de longo prazo, contexto, skills, agentes, voz, visão, integrações e automação segura.

## Identidade

- Nome falado e exibido normalmente: **Huli**.
- A sigla técnica é **HULI**.
- Significado conhecido internamente: **Humano Único Leal Inteligente**.
- Huli não deve repetir o significado da sigla ao se apresentar ou em respostas comuns.
- O significado só deve ser explicado quando o usuário perguntar explicitamente ou quando houver motivo técnico/documental.
- Nunca pronunciar o nome como “H ponto U ponto L ponto I”. O nome é **Huli**.

## Princípio de desenvolvimento

> Só avançamos de fase quando a anterior estiver funcionando, testada, documentada e salva no Git.

A arquitetura deve ser construída desde o início pensando em **PC + celular + servidor**, ainda que as primeiras versões sejam executadas apenas no computador.

## Estado atual

**Versão alvo:** `4.0.0-alpha.1`  
**Fase atual:** Fase 0 — Fundação arquitetural  
**Status:** planejamento e preparação do repositório.

## Roadmap

O plano mestre completo está em [`docs/ROADMAP.md`](docs/ROADMAP.md).

## Arquitetura base planejada

```text
HULI/
├── core/
├── brain/
├── memory/
├── skills/
├── agents/
├── api/
├── security/
├── integrations/
├── voice/
├── vision/
├── clients/
├── infrastructure/
├── tests/
├── docs/
└── main.py
```

## Regra arquitetural

Novas ideias não alteram arbitrariamente a arquitetura ou a ordem do projeto. Elas devem ser encaixadas na fase correspondente do roadmap.

## Segurança

Huli lidará futuramente com informações pessoais, credenciais, dispositivos e automações. Dados sensíveis, segredos, tokens, bancos locais e arquivos de ambiente nunca devem ser versionados no Git.
