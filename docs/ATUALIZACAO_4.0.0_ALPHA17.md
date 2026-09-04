# Huli 4.0.0-alpha.17

Atualização local de 04/09/2026 voltada à organização e acompanhamento do dia.

## Novas funções

- criação e conclusão de hábitos diários;
- visão de hábitos do dia, sequência atual e frequência nos últimos sete dias;
- sessões de foco de 1 minuto a 4 horas, com alerta ao terminar;
- escolha da prioridade atual usando agenda e tarefas reais;
- lembretes automáticos de compromissos nos 15 minutos anteriores ao horário.

## Exemplos

```text
criar hábito beber água
marque o hábito beber água como feito
meus hábitos
iniciar foco por 25 minutos para revisar proposta
qual é a minha prioridade agora?
```

Os lembretes da agenda são automáticos enquanto a Huli estiver aberta. O tempo
de antecedência pode ser ajustado pela configuração
`HULI_AGENDA_REMINDER_MINUTES`, entre 1 e 120 minutos.

## Segurança e persistência

- hábitos ficam no banco SQLite local e são separados por proprietário;
- a migração de banco 9 apenas cria tabelas novas e não altera registros
  anteriores;
- sessões de foco reutilizam temporizadores locais e são canceladas ao fechar;
- alertas de agenda são somente leitura e não alteram compromissos;
- nenhuma dessas funções transmite dados para serviços externos.

## Validação

- 350 testes automatizados aprovados;
- análise Ruff aprovada;
- integridade do banco anterior confirmada antes da migração;
- inicialização real e migração aditiva verificadas em `C:\HULI4`;
- nenhum conteúdo pessoal incluído no Git.
