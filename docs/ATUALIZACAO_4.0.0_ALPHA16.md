# Huli 4.0.0-alpha.16

Atualização local de 04/09/2026 com novas ferramentas para a rotina diária.

## Novas funções

- diagnóstico local e resumido de processador, memória, disco, bateria e tempo
  ligado;
- calculadora determinística com operações básicas, decimais e porcentagens;
- lista de compras persistente, separada das tarefas comuns;
- temporizadores locais de até 24 horas, com alerta visual e falado.

## Exemplos

```text
como está meu computador hoje?
quanto é 15% de 850?
adicione leite na lista de compras
o que falta comprar?
já comprei leite
temporizador de cinco minutos para o café
quais temporizadores ativos?
cancelar temporizador 1
```

## Segurança e privacidade

- o diagnóstico consulta apenas indicadores locais e não altera o sistema;
- a calculadora usa uma árvore de operações permitidas e nunca executa texto;
- a lista de compras reutiliza o banco local protegido pela sessão do
  proprietário;
- temporizadores existem somente durante a sessão e são cancelados ao fechar a
  Huli;
- nenhuma dessas funções envia conteúdo para serviços externos.

## Validação

- 340 testes automatizados aprovados;
- análise Ruff aprovada;
- inicialização real por `python main.py` aprovada;
- diagnóstico, cálculo e alerta de temporizador verificados na instalação
  `C:\HULI4`;
- nenhum dado pessoal foi adicionado ao Git.
