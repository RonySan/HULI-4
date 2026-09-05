# Huli 4.0.0-alpha.19

Correção local de 05/09/2026 para abertura do Spotify no Windows.

## Problema encontrado

O Windows mantinha `Spotify.exe` e `spotify_cli.exe` como aliases de execução
vazios, embora o aplicativo não estivesse registrado nem instalado. A Huli
encontrava um desses arquivos, respondia que estava abrindo o Spotify e o
Windows não iniciava nada.

## Correções

- “Spotify”, “esporte pai” e “esportes pai” continuam chegando à mesma intenção
  somente dentro do comando de abrir aplicativo;
- aliases vazios do Spotify dentro de `WindowsApps` deixam de ser tratados como
  uma instalação válida;
- uma instalação real ou um atalho válido continua tendo prioridade;
- sem instalação real, a Huli abre o endereço fixo e seguro do Spotify Web;
- o comando de músicas favoritas usa o aplicativo quando o protocolo `spotify:`
  existe e o Spotify Web quando ele não existe;
- a resposta informa quando foi necessário usar a versão Web.

## Como testar

Feche o painel antigo, abra novamente com `INICIAR_PAINEL.bat` e experimente:

```text
abrir Spotify
abrir esporte pai
tocar minhas favoritas
```

Nesta máquina, onde o aplicativo desktop não está registrado, os pedidos devem
abrir o Spotify Web no navegador padrão. Se o aplicativo desktop for instalado
depois, a Huli passa a priorizá-lo automaticamente.

## Validação

- reconhecimento testado com o nome correto e com as duas transcrições de voz;
- alias vazio do Windows coberto por teste de regressão;
- fallback Web restrito a endereços fixos do Spotify;
- nenhum aplicativo ou navegador real é aberto pelos testes automatizados.
