# Estrutura Oficial do Projeto

Esta estrutura é a base definitiva da linha Huli 4.x.

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
├── docs/
├── main.py
├── pyproject.toml
├── .env.example
└── .gitignore
```

## Decisão de namespace

Todo código principal da assistente fica dentro do pacote Python `huli`.

Isso evita módulos globais genéricos como `core`, `memory` e `security`, reduz conflitos de importação e permite que o mesmo núcleo seja usado futuramente por PC, servidor, web e aplicativo móvel.

## Responsabilidades

- `huli/core`: coordenação do ciclo de execução. O Kernel mora aqui e não deve acumular regras de domínio.
- `huli/brain`: interpretação, contexto e componentes cognitivos locais.
- `huli/memory`: mecanismos de persistência e recuperação de memória.
- `huli/skills`: capacidades especializadas acionadas pelo núcleo.
- `huli/agents`: agentes autônomos futuros. Não entram em operação antes da fase prevista.
- `huli/api`: interface de acesso ao núcleo para clientes externos.
- `huli/security`: autenticação, autorização e políticas de risco.
- `huli/integrations`: serviços e plataformas externas.
- `huli/voice`: entrada e saída de voz.
- `huli/vision`: visão computacional.
- `huli/clients`: contratos e componentes compartilhados com clientes PC/web/mobile.
- `huli/infrastructure`: banco, arquivos, rede, logging e adaptadores técnicos.
- `tests`: testes automatizados.
- `docs`: decisões, arquitetura e roadmap.

## Regra permanente

Novos recursos devem respeitar essas fronteiras. Se uma capacidade exigir mudança estrutural, a mudança precisa ser documentada como decisão arquitetural antes da implementação.
