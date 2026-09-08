# Huli 4.0.0-alpha.20

Atualização local de 08/09/2026 para melhorar a transcrição de comandos em
português do Brasil.

## Diagnóstico

O microfone estava funcionando. O problema principal era o reconhecedor Vosk
Small português, um modelo leve de 31 MB, e a captura que devolvia o primeiro
trecho encerrado por silêncio. Assim, uma frase podia chegar ao interpretador
somente como “pode”, embora ainda houvesse palavras seguintes.

## Melhorias

- Faster Whisper 1.2.1 e Whisper Small executados localmente em CPU com INT8;
- modelo versionado e instalado em `models/whisper-small`;
- áudio mantido somente em memória, sem gravação em arquivo;
- captura iniciada ao detectar fala e encerrada após uma pausa real;
- contexto de vocabulário para Huli, Spotify, agenda, tarefas e comandos comuns;
- Vosk agora junta começos incompletos como “pode” e “abrir” ao trecho seguinte;
- seleção automática: Whisper primeiro, Vosk como contingência e reconhecimento
  do Windows quando disponível;
- ativação Huli/Ruli continua separada no detector fonético leve;
- novo instalador `INSTALAR_VOZ_MELHORADA.bat` sem cobrança por uso.

## Instalação desta máquina

O Faster Whisper e o modelo Small já foram instalados localmente. O diagnóstico
confirmou:

```text
windows-tts+whisper-offline
microfone disponível
ganho digital 1.8x
detector fonético Huli/Ruli pronto
```

## Como testar

Feche todas as janelas antigas da Huli, abra `INICIAR_PAINEL.bat`, ligue a
escuta contínua e teste uma frase por vez:

```text
Huli
abrir Spotify

Huli
tocar minhas favoritas

Huli
como está a nossa agenda hoje?
```

Depois que a Huli detectar o nome, fale o comando ao aparecer “Estou ouvindo”.
O primeiro carregamento do modelo pode demorar alguns segundos; os seguintes
usam o modelo já carregado em memória.

## Privacidade e custo

Não há API paga nem cobrança recorrente. A conexão foi usada somente para
instalar a biblioteca e baixar o modelo uma vez. A transcrição posterior ocorre
no próprio computador.
