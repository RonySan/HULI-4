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

- **Versão:** `4.0.0-alpha.14`
- **Fase atual:** fundação antecipada da Fase 9 — Voz local no Windows
- **Módulo atual:** voz contínua, agenda natural, proprietário local e aplicativos
- **Branch de desenvolvimento:** `phase-9-voice-staging`

As regressões das Fases 0 a 4 são executadas antes da validação do diário. A
`main` continua protegida; código de staging só deve ser integrado depois da
validação local do usuário e do CI em Linux e Windows.
As Fases 5–8 não foram declaradas concluídas: apenas a interface local de voz foi
antecipada por decisão do proprietário, sem acoplar voz ao Kernel.

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
  ├── continuidade da conversa
  └── diário pessoal privado
        ↓
KernelResponse
        ↓
EventBus + SQLite
        └── diário: AES-256-GCM + índice cego

Interface local (Windows)
  ├── microfone → PocketSphinx/Vosk → Kernel
  └── KernelResponse → System.Speech → alto-falante
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
- `agenda.complete`
- `app.open`
- `task.create`
- `task.list`
- `task.complete`
- `smalltalk`
- `conversation.recap`
- `journal.create`
- `journal.list`
- `journal.search`
- `journal.update`
- `journal.delete`
- `journal.trash`
- `journal.restore`
- `journal.help`
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

A `alpha.10` entende variações naturais verificadas no uso real, como
“que dia é hoje?”, “como está nossa agenda essa noite?”, “agenda pra mim jantar
às 22 horas” e “o que conversamos mais cedo?”.

A `alpha.13` também entende `agendas` e `o que temos na agenda`, corrigindo as
duas frases que falharam na validação local.

A `alpha.14` adiciona ganho digital configurável do microfone, horários falados
em português, conclusão de compromissos, entrada local direta como Rony e
abertura segura de programas instalados no Windows.

A `alpha.11` acrescenta um diário explícito que não alimenta automaticamente a
Memory Engine nem o Knowledge Graph. Exemplos:

```text
diário: hoje foi um dia importante
diário: finalizei o projeto | humor: feliz | tags: trabalho, Huli
meu diário de hoje
procure no meu diário por família
edite a entrada #1 do diário: texto corrigido
apague a entrada #1 do diário
lixeira do meu diário
restaure a entrada #1 do diário
```

A `alpha.12` protege conteúdo, índice de busca, humor e etiquetas com
AES-256-GCM. A chave aleatória do diário é cifrada por uma chave derivada da
senha com scrypt. No Windows, o envelope recebe uma segunda camada DPAPI ligada
à conta atual. A busca usa hashes autenticados, sem gravar as palavras no banco.

Na primeira autenticação, entradas da alpha.11 são copiadas para um backup
criptografado, migradas em uma transação e removidas das páginas lógicas antigas
do SQLite. A chave aberta permanece apenas em memória e é bloqueada após 15
minutos sem uso, no logout ou no encerramento do terminal.

## Correções locais e voz em português — 31/08/2026

Esta instalação inclui correções de privacidade, sessão, busca de memória, agenda
e voz offline. Consulte [instruções e limites](docs/CORRECOES_2026_08_31.md).

- `INICIAR_HULI.bat`: iniciar pelo teclado.
- `INICIAR_PAINEL.bat`: abrir o painel com botões de voz.
- `INICIAR_COM_VOZ.bat`: falar e ouvir no modo proprietário local.
- `TESTAR_VOZ.bat`: teste real sem executar comandos nem acessar dados pessoais.
- `INSTALAR_VOZ_LOCAL.bat`: dependências opcionais e modelo português oficial.

A escuta usa Vosk local quando configurado. A fala continua usando a voz pt-BR
instalada no Windows. A configuração distingue fala, escuta e teste acústico.

## Voz local — fundação original alpha.13

A fala usa `System.Speech`; a escuta usa Vosk e a ativação usa PocketSphinx,
sempre localmente. Áudio e transcrições não são enviados a serviços externos.
O ganho digital padrão do microfone é `1.8x` e pode ser ajustado por
`HULI_VOICE_INPUT_GAIN` entre `0.5` e `4.0`.

Comandos disponíveis no terminal:

```text
voz                 mostra o estado da voz
ativar voz          fala automaticamente as respostas permitidas
desativar voz       desliga fala e modo contínuo
ouvir               escuta um único comando pelo microfone
modo voz            mantém a conversa por voz
parar voz           retorna ao teclado
```

O modo contínuo volta ao teclado após o tempo de inatividade. Respostas do
diário privado nunca são lidas automaticamente em voz alta. Interrupção durante
a fala e identificação biométrica de quem falou continuam planejadas para
evoluções posteriores da Fase 9.

Para o reconhecimento em português, o Windows precisa ter o pacote de fala
`Português (Brasil)` instalado em **Configurações > Hora e idioma > Idioma e
região > Português (Brasil) > Opções de idioma > Fala**.

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
powershell -ExecutionPolicy Bypass -File .\scripts\VALIDAR_FASE4_2.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\VALIDAR_VOZ.ps1
```

O CI executa em Linux e Windows nas branches `phase-*` e em `main`.

## Executar no terminal

```powershell
python main.py
```

## Abrir o painel

```powershell
.\INICIAR_PAINEL.bat
```

O painel possui os botões **Ouvir agora** e **Escuta contínua**. Depois de ligar
a escuta contínua, diga `Huli, que horas são?`. A fala é processada localmente;
ao começar a digitar, a ativação pausa para dar prioridade ao teclado.

O botão **Calibrar nome** pede cinco pronúncias isoladas de `Huli`. Um detector
fonético local procura somente os sons de `Huli/Ruli`; ele não transforma
`olhe`, `link`, `ruim` ou `único` no nome. O áudio não é salvo. A calibração
vale tanto para o painel quanto para `INICIAR_COM_VOZ.bat`.

Para falar e digitar na mesma sessão, use:

```powershell
.\INICIAR_COM_VOZ.bat
```

No modo proprietário local, a Huli aguarda o som de `Huli/Ruli` em segundo plano, sem
depender da transcrição do Vosk. Diga `Huli`, espere `Estou ouvindo` e então
fale o comando. Ao começar a digitar, o teclado tem prioridade e a captura
atual é cancelada.

Use `pausar ativação` ou `privacidade` para parar a escuta e `ativar Huli` para
retomá-la. O áudio é processado localmente em memória e não é salvo. O modo
sem microfone continua disponível em `.\INICIAR_HULI.bat`.

## Despertador e resumo matinal

`CONFIGURAR_DESPERTADOR.bat` registra no Windows o despertador diário das
05:50. Ele usa uma melodia local gratuita, oferece soneca de 10 minutos e pode
abrir o painel diretamente com fala e escuta contínua preparadas.

Ao dizer `Huli, bom dia`, o proprietário ouve a hora, somente os compromissos
do dia, o clima de São Paulo e uma sugestão curta de roupa. Sem internet, hora e
agenda continuam funcionando. O clima usa Open-Meteo e não exige chave.

Para testar o despertador imediatamente:

```powershell
.\TESTAR_DESPERTADOR.bat
```

Para trocar a melodia por um arquivo WAV local:

```powershell
.\CONFIGURAR_DESPERTADOR.bat -AudioPath "C:\Musicas\despertador.wav"
```

Consultas são executadas imediatamente. Comandos de voz que alteram dados ou
acessam o diário ficam pendentes por 30 segundos e só prosseguem quando o dono
digita `confirmar voz`; a confirmação também passa pelas permissões normais.

O painel e o terminal entram diretamente como `Rony` por padrão. Esse modo é
controlado por `HULI_LOCAL_LOGIN_ENABLED=false`; para restaurar a tela anterior
de proprietário/senha/visitante, defina o valor como `true`. A API local mantém
sua autenticação independentemente dessa opção.

O diário permanece bloqueado enquanto o login local estiver desativado, pois a
senha é necessária para abrir sua chave criptográfica. Para reativá-lo, habilite
o login local e use a senha existente. Para configurar ou trocar a senha:

```powershell
python tools/set_local_password.py
```

Exemplos da agenda e dos programas na `alpha.14`:

```text
agenda para amanhã reunião com Paulo às oito horas da manhã
concluir compromisso de hoje
abrir o Google Chrome
Huli, abra a calculadora
```

A Huli procura programas no Menu Iniciar, no registro de aplicativos do Windows
e em utilitários conhecidos. Ela não executa texto livre como PowerShell, não
aceita parâmetros, URLs, scripts ou caminhos fornecidos na conversa.

Senhas novas precisam ter pelo menos 8 caracteres. Senhas curtas criadas em
versões anteriores continuam aceitas apenas para permitir login, migração e
troca segura; a Huli recomendará a atualização.

Backup e restauração do diário:

```powershell
python tools/backup_journal.py
python tools/restore_journal.py
```

O backup `.hulibak` é portátil e criptografado pela senha usada no momento da
criação. Depois de trocar a senha da Huli, backups antigos continuam exigindo a
senha antiga. Sem a senha correta e sem um backup utilizável, o conteúdo não
pode ser recuperado — essa é uma propriedade da criptografia, não um defeito.

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
- [`docs/PHASE_4_1_JOURNAL.md`](docs/PHASE_4_1_JOURNAL.md)
- [`docs/PHASE_4_1_VALIDATION.md`](docs/PHASE_4_1_VALIDATION.md)
- [`docs/PHASE_4_2_VAULT.md`](docs/PHASE_4_2_VAULT.md)
- [`docs/PHASE_4_2_VALIDATION.md`](docs/PHASE_4_2_VALIDATION.md)
- [`docs/PHASE_9_VOICE_FOUNDATION.md`](docs/PHASE_9_VOICE_FOUNDATION.md)
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
│   ├── journal/
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

O diário exige proprietário autenticado e uma conta com senha, isola registros
por usuário, recusa senhas/tokens/chaves, não copia entradas para memória ou
conhecimento e remove o conteúdo dos eventos, interações técnicas e contexto
conversacional. O conteúdo, humor, etiquetas e dados de busca ficam cifrados em
repouso. Metadados operacionais — proprietário, data, sensibilidade, estado e
horários — continuam visíveis no SQLite.

Criptografia não substitui a proteção do computador. Mantenha a conta do
Windows protegida, o BitLocker ativo, backups fora do computador e nunca
registre credenciais no diário.

## Regra arquitetural

Novas ideias não alteram arbitrariamente a arquitetura ou a ordem do projeto. Elas devem ser encaixadas na fase correspondente do roadmap.
