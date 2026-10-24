# H.U.L.I. 4.0.0-alpha.17 — Spotify pessoal

**Status:** branch de desenvolvimento; execução real ainda não validada.

## Entrega
- OAuth 2.0 Authorization Code + PKCE; estado aleatório; callback exclusivo em loopback
  \`http://127.0.0.1:8767/callback\`. Não usamos localhost, client secret ou redirect público.
- Tokens criptografados com DPAPI do Windows atual; renovação de acesso automática.
- Listagem de playlists, reprodução de uma playlist pelo nome (sem escolhas ambíguas),
  pausa, retomada e avanço de faixa.
- Comandos determinísticos, que não dependem de um LLM.
- Acesso do celular/notebook pelo cliente privado Huli autenticado, se configurado.

## Pré-requisitos
- Spotify Premium e o aplicativo Spotify aberto em um dispositivo; a API de playback
  exige Premium e pode recusar dispositivos restritos.
- Uma conta Spotify Developer elegível; em modo de desenvolvimento, o proprietário
  do aplicativo precisa de Premium, sujeito aos limites vigentes.
- Windows 11, Python 3.11 usado pela Huli e pasta data com backup.
- Criar um app pessoal no painel https://developer.spotify.com/dashboard .
- Cadastrar exatamente a Redirect URI: \`http://127.0.0.1:8767/callback\`.
  HTTP é permitido apenas no endereço 127.0.0.1 (não use localhost).

## Conectar ao Spotify no PC principal
Abra o PowerShell, depois de fazer backup da pasta data:

\`\`\`powershell
cd C:\HULI4
git fetch origin
git switch phase-8-spotify-alpha17
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
$env:HULI_SPOTIFY_CLIENT_ID="COLE_AQUI_O_CLIENT_ID_PUBLICO"
.\.venv\Scripts\python.exe tools\spotify_connect.py
\`\`\`

Seu navegador solicitará autorização apenas para listar playlists, consultar
dispositivos e controlar reprodução. A Huli não pede acesso para modificar playlists.
Aceite no navegador. O callback espera no máximo 3 minutos.

Ao iniciar a Huli depois, defina novamente HULI_SPOTIFY_CLIENT_ID no mesmo
terminal ou ajuste o script de inicialização. O Python não carrega .env
automaticamente; inserir a variável apenas no arquivo .env não garante efeito.
Nunca cole senhas, códigos de autorização ou tokens no chat ou no GitHub.

## Exemplos
\`\`\`text
Huli, toque minha playlist Rock
Huli, tocar playlist de Linkin Park
Huli, quais são minhas playlists?
Huli, pause a música
Huli, continue a música
Huli, próxima faixa
\`\`\`

A Huli pedirá o nome da playlist se a frase estiver incompleta. Se houver
nomes parecidos, ela solicita o nome completo. Sem dispositivo ativo,
abra o aplicativo Spotify no PC/celular antes de tentar.

A API envia comandos à conta Spotify; o áudio é reproduzido pelo aplicativo
Spotify, não pela Huli. A Huli informa que *enviou* o comando, sem inventar
confirmação de playback real.

## Segurança e remoção
- Tokens locais em \`data/spotify_tokens.dpapi\`, cifrados com DPAPI para o usuário
  Windows atual. Não copie para outras máquinas; reconecte se migrar de PC.
- Para desconectar, revogue o app nas configurações do Spotify e, com a Huli
  fechada, apague apenas o arquivo spotify_tokens.dpapi.
- Nenhum Client Secret é usado; não publique access token nem refresh token.
- Não exponha a API/portas Spotify pela internet nem Tailscale Funnel.
- Não use a integração para redistribuição/transmissão comercial de música.
- Sem acesso remoto ao cofre, shell, diário ou tarefas de risco.

## Testar
\`\`\`powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pytest tests/test_spotify.py tests/test_multidevice.py
\`\`\`

Consulte a documentação oficial do Spotify: Authorization Code PKCE,
Redirect URIs, Scopes e Spotify Web API Start/Resume Playback.
