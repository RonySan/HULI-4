# H.U.L.I. alpha.18 — Spotify Connect e validação das branches

## O que mudou

Esta atualização acrescenta à alpha.17:
- Lista de dispositivos Spotify Connect detectados pela API oficial.
- Seleção explícita do dispositivo de reprodução por nome (ex.: notebook ou celular).
- Revalidação do ID antes de cada comando; o Spotify não garante IDs permanentes.
- Recusa de dispositivos restritos, desconectados ou nomes ambíguos.
- Volta ao dispositivo ativo com um comando de voz.
- Dois atalhos na interface web do notebook e Android: Dispositivos e Playlists.
- Testes automatizados de seleção, desaparecimento do dispositivo e autenticação remota.
- Script para testar quatro branches em checkouts temporários e não modificar a instalação atual.

## Exemplos de voz e texto

Huli, quais dispositivos do Spotify?

Huli, usar Spotify no Notebook Rony

Huli, toque minha playlist Rock

Huli, pause a música

Huli, usar Spotify no Celular Rony

Huli, continue a música

Huli, Spotify modo automático

A seleção **não** começa a reprodução. Depois de selecionar, solicite
explicitamente tocar/continuar. A Huli diz apenas que enviou o comando;
a confirmação real depende do aplicativo Spotify e de uma conta Premium.

Quando a conta ainda não estiver conectada, siga o manual
docs/SPOTIFY_ALPHA17.md. Não há login em conta Spotify na interface web;
a autorização é feita somente no computador principal, pelo usuário Windows.

## Quando chegar em casa

1. No PC principal, pare a Huli e faça BACKUP da pasta C:\HULI4\data
   sem copiar a pasta ao GitHub.
2. Abra o terminal do VS Code na pasta C:\HULI4 e confirme que há Python
   3.11 e .venv instalado, conforme README. Não apague dados locais.
3. Atualize e instale esta branch:

~~~powershell
cd C:\HULI4
git fetch origin
git switch phase-9-devices-alpha18
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
~~~

4. Para testar todas as versões experimentais em isolamento
   **sem trocar sua branch atual**:

~~~powershell
powershell -ExecutionPolicy Bypass -File .\scripts\VALIDAR_BRANCHES.ps1
~~~

Este script avalia em ordem: alpha.15, alpha.16, alpha.17 e alpha.18.
Ele executa Ruff e pytest usando worktrees descartáveis no diretório TEMP,
sem usar C:\HULI4\data. Cada checkout ainda depende das dependências do
seu .venv e precisa de Internet para git fetch. Salve as mensagens do
terminal caso algum teste falhe.

5. A seguir execute a Huli alpha.18 usando a mesma configuração de login
   e conexão privada descrita em docs/MULTIDISPOSITIVO_ALPHA15.md.
   Abra http://127.0.0.1:8765/app no PC principal.
6. Configure Spotify uma única vez no PC seguindo
   docs/SPOTIFY_ALPHA17.md. Selecione dispositivos e playlist para
   realizar o teste com sua conta real.
7. No notebook e Android, com Tailscale conectado, utilize exclusivamente
   o HTTPS privado exibido por tailscale serve status, adicionando /app.
   Não abra portas públicas no roteador e não use Funnel.

## Limitações da alpha.18

- Não há APK nativo, wake word contínua no Android ou Spotify player embutido.
- A preferência pelo dispositivo fica apenas em memória no servidor Huli.
  Reiniciar a Huli volta automaticamente ao dispositivo ativo.
- Alguns dispositivos Connect não aparecem na API, ou aparecem como restritos.
- É necessário autenticar-se na Huli; a integração Spotify não tem token no
  navegador, apenas no usuário Windows principal.
- Não foram realizados testes com a sua conta Spotify real.
- Testes GitHub Actions validam lógica no Linux/Windows usando mocks, não
  substituem testes da rede Tailscale, Bluetooth, áudio e dispositivos reais.

Referências oficiais Spotify:
https://developer.spotify.com/documentation/web-api/reference/get-a-users-available-devices
https://developer.spotify.com/documentation/web-api/reference/start-a-users-playback
