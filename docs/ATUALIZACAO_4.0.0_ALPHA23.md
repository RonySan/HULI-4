# Huli 4.0.0-alpha.23

Atualização de confiabilidade para a inicialização automática no Windows.

## O que mudou

- a entrada do Windows agora identifica explicitamente que é uma partida automática;
- a Huli grava apenas o estado técnico `starting`, `ready` ou `failed` em
  `data/desktop_startup.json`;
- caso o painel não consiga abrir após o login, o motivo fica disponível em vez de
  desaparecer silenciosamente junto com o `pythonw`;
- o diagnóstico agora mostra a entrada registrada, o comando esperado e o último
  resultado: `python -m tools.configure_windows_startup diagnose`.

Não há conteúdo de conversas, diário, agenda ou voz nesse registro.

## Como confirmar

```powershell
cd C:\HULI4
.venv\Scripts\python.exe -m tools.configure_windows_startup diagnose
```

Após o próximo login do Windows, o resultado esperado é `ready`. A Huli abre
minimizada na bandeja; procure o ícone azul **H** perto do relógio.
