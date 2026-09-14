# Huli 4.0.0-alpha.27

Atualização de confiabilidade da agenda Google e do reconhecimento de voz.

## Correções

- A sincronização reutiliza exatamente o escopo OAuth já autorizado. Um token com
  permissão de escrita também pode consultar eventos sem gerar `invalid_scope`.
- Falhas de renovação e consulta ao Google Calendar agora retornam mensagens claras,
  sem expor detalhes internos ou credenciais.
- O vocabulário do Whisper inclui Google Calendar, agenda do Google e consultas da
  semana.
- A transcrição real observada para “Google Calendar hoje” recebe uma correção exata
  e limitada a essa consulta de agenda. Frases comuns com “grupo calendário” não são
  alteradas.

## Segurança

A correção de voz não usa aproximação ampla nem transforma palavras comuns em nome
ou comando. Ela só normaliza duas formas completas e conhecidas de uma consulta de
leitura da agenda.
