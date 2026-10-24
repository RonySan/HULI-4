# H.U.L.I. 4.0.0-alpha.16 — conversa local com Ollama

Esta fase adiciona respostas por IA local **apenas** quando a Huli não reconhece
uma intenção já implementada. Agenda, tarefas, memória, ações locais e política
de comandos remotos continuam no roteador existente.

## Windows — PC principal

1. Faça backup de `C:\\HULI4\\data`. Instale o Ollama pelo site oficial:
   https://ollama.com/download/windows
2. Abra o PowerShell e baixe um modelo local em português:

   ```powershell
   ollama pull qwen2.5:7b
   ollama list
   ```

3. No PowerShell que **iniciará a Huli**:

   ```powershell
   cd C:\\HULI4
   git fetch origin
   git switch phase-7-ollama-alpha16
   .\\.venv\\Scripts\\python.exe -m pip install -e ".[dev]"
   $env:HULI_LLM_ENABLED="true"
   $env:HULI_LLM_MODEL="qwen2.5:7b"
   .\\INICIAR_HULI_WEB.bat
   ```

4. Abra `http://127.0.0.1:8765/app`, faça login e faça uma pergunta livre.
   Em outro teste, mande `ping` e confira que o comando tradicional funciona.
5. Se o Ollama não responder, a Huli mostra uma mensagem de indisponibilidade,
   sem encaminhar a conversa para provedores externos. A integração vem
   desativada por padrão.

## Segurança e limites

- A API do Ollama é chamada somente em `127.0.0.1:11434`; não abra essa
  porta nem a porta da Huli no roteador.
- A IA **não** executa comandos, não usa ferramentas, não lê memória/diário,
  não controla contas ou Spotify e não acessa automaticamente a internet.
- O bloqueio de comandos remotos sensíveis continua ativo. A conversa remota
  só funciona após autenticação e configuração consciente de Tailscale Serve,
  conforme `docs/MULTIDISPOSITIVO_ALPHA15.md`.
- Não instale modelos Ollama `:cloud` para esta fase local.
- O histórico curto da Huli não é enviado ao modelo nesta fase; cada chamada
  é independente. É possível melhorar contexto depois de uma revisão de privacidade.
- A versão não foi validada no computador nem no Android do proprietário.

## Testes

```powershell
.\\.venv\\Scripts\\python.exe -m pytest -q tests/test_ollama_skill.py tests/test_multidevice.py
```

## Integração Spotify (ainda não implementada)

A reprodução de uma playlist específica exige autenticação/autorização da
conta Spotify e seleção do dispositivo de reprodução. Esta fase não envia
comandos de música; nunca relata que iniciou reprodução sem confirmação real.
