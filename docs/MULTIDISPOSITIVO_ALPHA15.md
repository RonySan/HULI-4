# HULI 4.0.0-alpha.15 — Interface multidispositivo (staging)

## Entregas desta etapa

- Interface web responsiva em `/app`, para Windows, notebooks leves e Android.
- A mesma API e o mesmo banco SQLite usados pelo Kernel atual: sem duplicar assistente nem memória.
- Login com token de sessão **mantido apenas na memória da aba**; logout revoga o token.
- Mensagens de texto, comandos rápidos, voz de resposta via navegador (opcional) e microfone sob demanda.
- Atalho de tela inicial Android via manifest (a instalação como PWA depende das regras do navegador).
- Modo de API privada: exige senha de pelo menos oito caracteres, rejeita `/v1/auth/setup`, limita tentativas de login e aceita apenas intenções remotas explícitas.
- Política de cache e CSP defensivos no cliente web.

**Atenção:** esta versão não inclui Ollama, novos modelos de IA, wake word no Android, notificações push, biometria, histórico visual persistente ou agentes remotos. A conversa entre dispositivos compartilha o contexto de curto prazo enquanto o processo central estiver ativo; o SQLite já mantém dados e operações da Huli, mas nem toda conversa vira memória permanente.

## Pré-requisitos

1. Windows 11 no computador principal, Python **3.11** e uma cópia de segurança da pasta `data`.
2. Conta do proprietário já cadastrada localmente.
3. Atualizar a senha usando `python tools/set_local_password.py` — pelo menos oito caracteres, de preferência uma senha longa exclusiva.
4. Cliente Tailscale instalado no PC principal, notebook e Android, com os três aparelhos conectados à **mesma tailnet**.
5. Nunca publicar a porta 8765 no roteador, nem usar **Tailscale Funnel**. O servidor deve continuar no endereço `127.0.0.1`.

## Instalação da branch no PC principal (PowerShell)

> Se a Huli já estiver instalada em `C:\HULI4`, faça backup da pasta `data`, pare a Huli e use a pasta existente, sem apagar seus dados.

```powershell
cd C:\HULI4
git fetch origin
git switch phase-6-multidevice-alpha15
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe tools\set_local_password.py
```

Se for uma instalação nova, faça o clone do repositório para uma pasta sua, mude para esta branch e configure o proprietário localmente com `python main.py` antes de ligar a API privada.

## Iniciar e testar localmente

Execute `INICIAR_HULI_WEB.bat`. No próprio PC, abra:

```text
http://127.0.0.1:8765/app
```

Use o mesmo proprietário e a senha forte cadastrada localmente. A API e a interface só estarão disponíveis enquanto o processo iniciado estiver em execução.

Para verificar o serviço: `http://127.0.0.1:8765/health`.

## Notebook e Android — conexão pela internet móvel ou Wi-Fi

No **PC principal**, com Tailscale instalado e conectado, abra PowerShell como administrador e execute:

```powershell
tailscale serve --bg 8765
tailscale serve status
```

O comando `status` informa o endereço privado HTTPS do serviço, semelhante a `https://nome-do-pc.nome-da-rede.ts.net`. Abra no notebook ou no Android **conectado ao Tailscale** e acrescente `/app`.

- No notebook use Edge/Chrome e um microfone, se desejar.
- No Android abra o endereço no Chrome. Opcionalmente, no menu do navegador escolha **Adicionar à tela inicial** ou **Instalar app**, conforme disponível.
- Para parar o compartilhamento na tailnet: `tailscale serve off` (ou consulte `tailscale serve status`).

O Tailscale Serve encaminha o tráfego HTTPS para a API que continua escutando apenas no loopback local. **Não use Funnel**, redirecionamento de porta no roteador ou domínio público para esta versão.

## Cuidados de segurança

- `HULI_REMOTE_ACCESS_ENABLED=true` é definido por `INICIAR_HULI_WEB.bat`. O modo privado exige senha forte na API, desabilita cadastro de dono e limita tentativas.
- Comandos remotos de abrir programas (`app.open`), diário, exclusão de memórias e outras intenções não autorizadas retornam HTTP 403. Esses comandos permanecem disponíveis apenas pelas interfaces locais já existentes, de acordo com suas regras.
- A interface web não guarda tokens em localStorage, cookies ou IndexedDB. Uma atualização de página encerra a sessão da aba.
- Habilite proteção por tela/senha em todos os aparelhos e limite os membros da tailnet.
- A opção de **microfone do navegador** pode processar fala em serviços externos do próprio navegador. Ela requer consentimento e não oferece escuta contínua. Não use para informações sigilosas.
- A síntese de voz também depende do navegador e das vozes instaladas.
- O diário pessoal criptografado permanece bloqueado na interface remota desta etapa.
- Não publique senhas, backups, tokens, arquivos `.env` ou conteúdo da pasta `data` no Git.

## Verificação automatizada

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_multidevice.py
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
```

Teste prático: inicie o serviço, entre no computador, pergunte "que horas são?", crie um compromisso e consulte a agenda no Android conectado à tailnet. Os dados são executados no mesmo processo e persistidos no mesmo banco.

## Itens posteriores

1. Teste real na rede privada e correções de interoperabilidade Windows/Android.
2. Provedor de LLM híbrido com controle de dados e orçamento de GPU.
3. Histórico visual persistente com filtragem por usuário.
4. App Android dedicado, notificações e captura de mídia autorizada.
5. Agent local para comandos no notebook, com consentimento por ação.
6. Segurança de produção, recuperação de conta e proteção adicional contra automação abusiva.
