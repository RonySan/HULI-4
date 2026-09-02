# Correções locais — 31/08/2026

Esta atualização corrige problemas confirmados na revisão da alpha.13. Não migra nem apaga registros pessoais, não altera senhas e não adiciona IA generativa nem operador do computador.

## Correções

- Segredos reconhecidos pela política são recusados antes de chegar às Skills, eventos ou histórico. O contexto e a transcrição exibida recebem proteção adicional. A detecção é conservadora e não consegue identificar toda sequência secreta sem contexto.
- O terminal verifica o token em cada comando e solicita autenticação quando a sessão foi revogada ou expirou.
- A busca de memórias percorre todos os registros do proprietário, com leitura em lotes e resultados limitados após a classificação, não antes.
- O diretório padrão de dados fica ancorado na instalação. Caminhos relativos em HULI_DATA_DIR também são relativos à instalação; caminhos absolutos continuam aceitos.
- A agenda aplica manhã (00–12h), tarde (12–18h) e noite (18–24h), inclusive amanhã. “Trabalho” não é apresentado como integração de calendário: a consulta continua sendo à agenda local.
- “Como vai Huli?”, “o que temos pra hoje à tarde?” e “trocador de calor verificado” são reconhecidos. Concluir tarefas e cancelar compromissos por descrição ambígua solicita o número em vez de escolher o primeiro.

## Voz local

- Fala: voz pt-BR instalada no Windows.
- Escuta: PocketSphinx detecta foneticamente Huli/Ruli; depois, Vosk entende o comando em português. Tudo funciona localmente, sem conta de API.
- O microfone só abre quando se pede `ouvir`, `modo voz`, o inicializador com ativação ou um teste explícito de microfone.
- Não há gravação em disco. A fila de áudio é limitada e o dispositivo é fechado ao terminar, cancelar ou falhar.
- Frases incompletas no limite de tempo e reconhecimento de baixa confiança não são executados.
- O inicializador com voz mantém uma ativação local em segundo plano. Somente os sons de “Huli/Ruli” ativam; “olhe”, “link”, “ruim” e “único” são recusados.
- O painel permite validar o detector fonético com cinco amostras. Nenhum áudio é salvo.
- Ao começar a digitar, o teclado cancela a captura corrente e tem prioridade. `pausar ativação` ou `privacidade` interrompe a escuta; `ativar Huli` retoma.
- Consultas de voz são imediatas. Alterações de agenda, tarefas, projeto, memória ou diário aguardam `confirmar voz` digitado por até 30 segundos.
- O diário não é lido automaticamente. A voz não identifica biometricamente quem está falando: mantenha controle físico de uma sessão autenticada.

## Como usar

Abra `C:\HULI4\INICIAR_COM_VOZ.bat` e faça seu login. Diga “Huli”, aguarde “Estou ouvindo” e fale o comando. Você pode digitar normalmente no mesmo prompt.

Para usar teclado, abra `C:\HULI4\INICIAR_HULI.bat`. Dentro da Huli:

```text
voz
ativar voz
ouvir
modo voz
parar voz
pausar ativação
ativar Huli
privacidade
```

`C:\HULI4\TESTAR_VOZ.bat` reproduz uma frase e transcreve uma resposta, sem executar ações e sem acessar o banco pessoal.

## Configuração opcional

As opções são variáveis de ambiente; o arquivo `.env.example` é documentação, não é carregado automaticamente.

```text
HULI_VOICE_INPUT_PROVIDER=auto
HULI_VOICE_MODEL_PATH=models/vosk-pt
HULI_VOICE_INPUT_DEVICE=
HULI_VOICE_INPUT_TIMEOUT=20
HULI_VOICE_AUTO_SPEAK=false
HULI_VOICE_START_LISTENING=false
HULI_VOICE_WAKE_ENABLED=false
HULI_VOICE_WAKE_CYCLE_TIMEOUT=30
```

`HULI_VOICE_INPUT_DEVICE` aceita o número ou parte do nome do microfone. Consulte dispositivos com `.venv\Scripts\python.exe -m sounddevice`. Se o padrão não captar sua voz, selecione o microfone correto e reinicie.

## Validação e limites

Resultado local atualizado em 01/09/2026:

- 287 testes aprovados; Ruff e verificação do diff sem problemas.
- Validadores das fases 0, 1, 2, 3, 4, 4.1, 4.2, intenção e voz lógica aprovados.
- Síntese de uma frase executada no Windows.
- Microfone aberto por dois segundos, com sinal detectado e sem perda de áudio; nenhuma gravação ou transcrição desse teste.
- Modelo Vosk carregado e três frases artificiais reconhecidas corretamente: “bom dia”, “que horas são”, “o que temos na agenda”. Isso não substitui o teste com a voz do usuário.
- A suíte de segurança foi executada no contexto normal do Windows porque o ambiente restrito não disponibiliza DPAPI/vozes da mesma maneira.

Os testes automatizados usam áudio e dispositivos simulados; aprovação deles não comprova qualidade acústica. `tools.diagnose_voice` consulta os motores reais e carrega o modelo. As opções `--speak`, `--listen` e `--microphone-test` realizam testes explícitos de hardware.

O bloqueio de segredos vale para novas entradas. Históricos antigos foram preservados e podem conter dados gravados antes da correção; uma limpeza retroativa exige um procedimento separado de revisão e proteção dos backups.

A senha opcional fora do diário e a ausência de proteção avançada contra tentativas de login continuam exigindo que a API seja usada somente localmente. Esta atualização não apresenta o sistema como pronto para exposição à internet.

Referências: [Vosk oficial e funcionamento offline](https://alphacephei.com/vosk/), [modelo português](https://alphacephei.com/vosk/models), [sounddevice](https://python-sounddevice.readthedocs.io/en/0.5.3/installation.html).
