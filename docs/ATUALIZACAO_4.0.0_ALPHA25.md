# Huli 4.0.0-alpha.25

Esta atualização reúne cinco melhorias de rotina diária:

- avisos de agenda para compromissos próximos e recém-atrasados;
- briefing matinal e painel **Hoje** com agenda e tarefas;
- escuta contínua que permanece ativa depois de chamados sem frase completa;
- criação no Google Calendar somente com confirmação na tela;
- novo atalho `AUTORIZAR_GOOGLE_CALENDAR_ESCRITA.bat` para conceder a permissão
  adicional necessária à criação de eventos.

Para criar um evento no Google, a pessoa proprietária pode dizer ou digitar:

```text
agende reunião com Ana amanhã às 10 no Google
```

A Huli mostra data, horário e título e só envia o evento depois de clicar em
**Sim**. A permissão de escrita não é ativada automaticamente: execute o novo
atalho e autorize a conta no navegador uma única vez.
