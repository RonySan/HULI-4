# Huli 4.0.0-alpha.24

Integração local segura com o Google Calendar.

- sincroniza eventos do calendário principal em modo somente leitura;
- marca eventos importados como `[Google]`;
- incorpora-os à agenda, resumo diário, briefing e alertas;
- atualiza automaticamente a cada 15 minutos enquanto a Huli estiver ativa;
- protege o token OAuth com DPAPI da conta atual do Windows;
- não cria, edita ou cancela eventos no Google;
- compromissos Google não podem ser concluídos ou cancelados por comandos locais.

Consulte [GOOGLE_CALENDAR.md](GOOGLE_CALENDAR.md) para conectar a conta.
