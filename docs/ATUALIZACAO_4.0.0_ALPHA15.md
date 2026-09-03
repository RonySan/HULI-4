# Huli 4.0.0-alpha.15

Atualização local de 03/09/2026 para compreensão de comandos após a palavra de
ativação.

## Correções

- “abrir o esporte pai” é corrigido para Spotify somente no contexto de abrir
  aplicativos;
- o executável interno `spotify_cli.exe` é apresentado como `Spotify`;
- “pode tocar as minhas favoritas” abre a coleção de músicas curtidas do
  Spotify e inicia a reprodução;
- comandos locais para tocar, pausar, parar, próxima e música anterior;
- janela do comando após “Huli” ampliada de 8 para 12 segundos;
- rearme de 3 segundos após chamado incompleto;
- detector Huli/Ruli um passo mais seletivo contra falsos chamados.

## Exemplos

```text
Huli, pode tocar as minhas favoritas
Huli, pause a música
Huli, próxima música
Huli, volte para a música anterior
Huli, abrir o Spotify
```

As correções fonéticas de Spotify não são aplicadas a textos gerais, agenda,
memória ou diário. Os controles usam somente o protocolo fixo do Spotify e os
comandos multimídia oficiais do Windows; nenhum texto é executado como shell.

## Validação

- 324 testes automatizados aprovados;
- análise Ruff aprovada;
- áudio sintético local: Huli/Ruli detectados;
- áudio sintético local: “olhe” e “o link” rejeitados;
- protocolo `spotify:` confirmado no Windows;
- nenhum aplicativo ou música foi aberto durante os testes automatizados.
