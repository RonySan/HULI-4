# Plano Mestre da Huli 4

## Regra principal

> Só avançamos de fase quando a anterior estiver funcionando, testada, documentada e salva no Git.

A Huli deve nascer preparada para evoluir como uma única assistente entre PC, celular, web e servidor, ainda que as primeiras versões rodem apenas no computador.

## Ciclo obrigatório de cada módulo

```text
ESPECIFICAÇÃO
↓
ARQUITETURA
↓
IMPLEMENTAÇÃO
↓
TESTES AUTOMÁTICOS
↓
TESTE COM O USUÁRIO
↓
CORREÇÃO
↓
DOCUMENTAÇÃO
↓
GIT
↓
PRÓXIMO MÓDULO
```

Novas ideias entram na fase correspondente. Elas não mudam arbitrariamente a arquitetura nem atropelam a ordem do projeto.

---

## Fase 0 — Fundação arquitetural

Objetivo: criar o esqueleto definitivo da plataforma.

Inclui:
- Kernel mínimo;
- sistema de Skills;
- eventos internos;
- configuração centralizada;
- logs estruturados;
- persistência/banco inicial;
- API base;
- autenticação;
- segurança;
- padrões de código;
- testes;
- documentação.

Critério de conclusão:

```text
Huli inicia
↓
autentica
↓
recebe mensagem
↓
Kernel interpreta
↓
Skill responde
↓
interação é registrada
```

Não entra inteligência sofisticada nesta fase.

---

## Fase 1 — Cérebro básico

Objetivo: fazer a Huli funcionar como assistente local organizada.

Módulos:
- Intent Engine;
- Context Engine;
- Skill Registry;
- Planner;
- Agenda;
- Daily Summary;
- Small Talk;
- Project Context.

Operações simples devem funcionar sem OpenAI quando não houver necessidade real de IA externa.

---

## Fase 2 — Memory Engine 4.0

Objetivo: criar memória de longo prazo rastreável.

Tipos previstos:
- memória episódica;
- memória semântica;
- memória de pessoas;
- memória de projetos;
- preferências;
- memória temporal.

Inclui aprendizado automático controlado. Informações sensíveis obedecem regras mais rígidas e a memória nunca deve inventar fatos.

---

## Fase 3 — Conhecimento pessoal

Objetivo: transformar memórias isoladas em relações compreensíveis.

Será criado um Knowledge Graph para relacionar:
- pessoas;
- família;
- trabalho;
- clientes;
- projetos;
- empresas;
- sistemas;
- equipamentos;
- lugares;
- compromissos;
- decisões.

---

## Fase 4 — Personalidade e conversa

Objetivo: construir uma personalidade consistente sobre uma base já capaz de lembrar e compreender contexto.

Inclui:
- personalidade consistente;
- humor;
- estilo variável;
- contexto emocional;
- conversa natural;
- reconhecimento de assunto;
- continuidade;
- comportamento adequado ao contexto.

### Fase 4.1 — Diário pessoal privado

Evolução intermediária concluída antes da inteligência híbrida:

- diário explícito e persistente;
- separação total da memória automática e do Knowledge Graph;
- consulta por data e busca textual;
- humor declarado e etiquetas opcionais;
- edição e exclusão lógica por identificador;
- lixeira privada e restauração por identificador;
- acesso exclusivo do proprietário;
- redação do conteúdo em eventos, interações técnicas e contexto curto;
- bloqueio de senhas, tokens e chaves;
- mesma capacidade no terminal e na API autenticada.

A criptografia em repouso depende de um cofre de chaves adequado e permanece
planejada como endurecimento posterior. A alpha atual não simula criptografia
guardando uma chave ao lado do banco.

### Fase 4.2 — Cofre pessoal seguro

Endurecimento concluído na `4.0.0-alpha.12`:

- AES-256-GCM para conteúdo, busca, humor e etiquetas;
- chave mestra aleatória envolvida por scrypt e senha do proprietário;
- segunda camada DPAPI na conta atual do Windows;
- índice cego HMAC para pesquisa sem palavras legíveis no SQLite;
- migração transacional da alpha.11 com backup criptografado anterior;
- limpeza lógica de páginas legadas e truncamento do WAL;
- bloqueio da chave em memória por inatividade, logout e encerramento;
- troca de senha com reenvelopamento da chave e revogação de sessões;
- backup portátil `.hulibak`, restauração autenticada e cópia de segurança
  automática antes de substituir o diário atual.

Metadados necessários para operação continuam visíveis. A Fase 4.2 não adiciona
inferência emocional, diagnóstico ou aprendizagem automática a partir do diário.

---

## Fase 5 — Inteligência híbrida

Objetivo: decidir corretamente entre recursos locais e modelos de IA.

Fluxo conceitual:

```text
HULI LOCAL
↓
MEMÓRIA
↓
SKILLS
↓
PLANNER
↓
AGENTES
↓
AI GATEWAY
```

Política planejada:
1. resolver localmente quando possível;
2. usar OpenAI quando raciocínio avançado realmente agregar valor;
3. usar modelo local como contingência offline conforme configuração futura.

---

## Fase 6 — Huli Server

Objetivo: centralizar cérebro, memória e identidade.

```text
             HULI SERVER
                  │
        ┌─────────┼─────────┐
        │         │         │
       PC      Celular     Web
```

A conversa deve continuar entre dispositivos sem criar memórias separadas.

---

## Fase 7 — Aplicativo móvel

Android primeiro.

Previsto:
- conversa;
- voz;
- histórico;
- tarefas;
- agenda;
- notificações;
- câmera;
- memória;
- projetos;
- status de dispositivos.

Suporte a iOS poderá ser acrescentado depois.

---

## Fase 8 — Agente do computador

Objetivo: criar um HULI PC Agent conectado ao servidor.

Poderá, mediante autorização:
- abrir programas;
- localizar arquivos;
- verificar estado do PC;
- capturar tela quando autorizado;
- executar scripts;
- iniciar serviços;
- monitorar aplicações.

Ações perigosas exigem confirmação.

---

## Fase 9 — Voz

### Fundação antecipada — `4.0.0-alpha.13`

Por decisão do proprietário, a interface local mínima foi antecipada sem marcar
as Fases 5–8 como concluídas e sem mover responsabilidades para o Kernel:

- síntese local pelo `System.Speech` do Windows;
- reconhecimento local de um comando pelo microfone;
- modo de conversa contínua com saída por inatividade;
- comandos de voz tratados pela interface local depois da autenticação;
- respostas do diário privado bloqueadas na fala automática;
- configuração de idioma, velocidade, volume e tempo de escuta;
- testes com backend substituível, sem exigir áudio no CI.

A fundação não inclui palavra de ativação, biometria de voz nem XTTS. Esses itens
continuam no escopo completo da Fase 9.

Fluxo previsto:

```text
Microfone
↓
Speech-to-Text
↓
Identificação do usuário
↓
Huli
↓
Resposta
↓
XTTS
```

Evoluções posteriores:
- palavra de ativação;
- interrupção durante fala;
- conversa contínua;
- reconhecimento de quem falou;
- múltiplos dispositivos.

---

## Fase 10 — Visão

Objetivo: interpretar entradas visuais autorizadas.

Fontes previstas:
- webcam;
- câmera do celular;
- screenshots;
- imagens;
- documentos;
- objetos.

---

## Fase 11 — Agentes autônomos

Somente depois de memória, segurança e contexto estarem sólidos.

Estrutura prevista:

```text
Supervisor
├── Project Agent
├── Research Agent
├── System Agent
├── Calendar Agent
├── Memory Agent
├── Communication Agent
└── Automation Agent
```

O Supervisor coordena agentes especializados.

---

## Fase 12 — Auto Planejamento

Objetivo: permitir que a Huli trabalhe com objetivos, não apenas comandos.

Um objetivo poderá ser decomposto em etapas, validado e executado conforme permissões e riscos.

Exemplo conceitual:

```text
objetivo
↓
planejamento
↓
verificações
↓
confirmações necessárias
↓
execução
↓
validação do resultado
```

---

## Fase 13 — Integrações

Cada integração será um módulo independente.

Previstas:
- e-mail;
- calendário;
- GitHub;
- WhatsApp;
- Home Assistant;
- câmeras;
- TV;
- iluminação;
- servidores;
- sistemas da Impulso;
- Medynx;
- OSSisten;
- outras integrações futuras.

---

## Fase 14 — Casa inteligente

Objetivo: permitir automação residencial contextual e segura.

Arquitetura prevista:

```text
HULI Core
↓
Automation Agent
↓
Home Integration
```

A lógica de dispositivos não será colocada diretamente no núcleo.

---

## Versionamento

Durante construção:

```text
4.0.0-alpha.1
4.0.0-alpha.2
4.0.0-alpha.3
...
4.0.0-beta.1
...
4.0.0-rc.1
...
4.0.0
```

- **Alpha:** construção ativa.
- **Beta:** recursos principais funcionando, ainda em validação.
- **RC:** candidata a produção.
- **4.0.0:** primeira versão estável da nova arquitetura.

## Ponto atual

```text
Huli 4.0
├── Fases 0–3
│   └── regressões automatizadas preservadas
├── Fase 4 staging
    ├── personalidade, conversa e linguagem natural — 4.0.0-alpha.10
    ├── diário pessoal privado — 4.0.0-alpha.11
    └── cofre pessoal seguro — 4.0.0-alpha.12
└── Fundação antecipada da Fase 9
    └── voz local do Windows e agenda natural — 4.0.0-alpha.13
```

A primeira HULI permanece como referência histórica. A nova Huli reaproveita
conhecimento e decisões válidas, mas não herda a arquitetura antiga por cópia.
A fundação de voz antecipada não altera a ordem restante: a Fase 5 continua sendo
a próxima fase estrutural depois da estabilização formal da Fase 4.2.
