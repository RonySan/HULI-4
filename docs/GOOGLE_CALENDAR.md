# Google Calendar na Huli

A Huli sincroniza o calendário principal do Google para a agenda local,
briefing e lembretes. A conexão inicial é **somente leitura**.

## Preparação única

1. Abra o [Google Cloud Console](https://console.cloud.google.com/).
2. Crie ou selecione um projeto chamado, por exemplo, `Huli Pessoal`.
3. Habilite a **Google Calendar API**.
4. Em **Google Auth Platform > Clients**, crie uma credencial do tipo
   **Desktop app**.
5. Baixe o JSON e salve-o com este nome exato:

   ```text
   C:\HULI4\credentials\google_calendar_oauth.json
   ```

O arquivo de credencial não é enviado ao Git. No primeiro uso a Huli abre a
tela oficial do Google; escolha a conta desejada e aceite somente a permissão
de leitura dos eventos.

## Conectar

```powershell
cd C:\HULI4
.\INSTALAR_GOOGLE_CALENDAR.bat
.\CONECTAR_GOOGLE_CALENDAR.bat
```

Após a autorização, a Huli importa os próximos 90 dias e atualiza a agenda a
cada 15 minutos enquanto estiver ativa. Para sincronizar manualmente:

```powershell
.venv\Scripts\python.exe -m tools.google_calendar sync
```

Para conferir o estado:

```powershell
.venv\Scripts\python.exe -m tools.google_calendar status
```

## Criar eventos diretamente

A Huli não recebe permissão de escrita automaticamente. Se você quiser que ela
crie eventos diretamente a partir dos seus pedidos, execute uma única vez:

```powershell
.\AUTORIZAR_GOOGLE_CALENDAR_ESCRITA.bat
```

O navegador pedirá uma nova autorização, agora para criar eventos. Depois, use
um comando como:

```text
agende reunião com Ana amanhã às 10 no Google
```

A Huli cria o evento imediatamente quando o pedido mencionar explicitamente
“Google” ou “Google Calendar”. Ela informa o resultado e sugere ajustes quando
detectar conflito ou pouco intervalo. Ela ainda não edita nem cancela eventos
do Google.

## Privacidade

O token de acesso fica em
`C:\HULI4\data\secrets\google_calendar_token.json`, protegido pelo DPAPI da
sua conta do Windows. Ele não é salvo em memória, diário, conversas ou Git.
Para desconectar a conta deste computador:

```powershell
.venv\Scripts\python.exe -m tools.google_calendar disconnect
```
