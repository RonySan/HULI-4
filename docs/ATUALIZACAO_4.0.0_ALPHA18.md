# Huli 4.0.0-alpha.18

Correção local de 05/09/2026 baseada em frases reais da escuta contínua.

## Melhorias

- consulta de compromissos do mês e da semana;
- comando composto para abrir Spotify e tocar as músicas favoritas;
- reconhecimento de “esporte pai” e “esportes pai” somente no contexto do
  Spotify;
- criação de hábito com singular, plural e a forma “hábitos para...”;
- calculadora com números falados em português, incluindo milhares, milhões e
  decimais;
- sequências numéricas ambíguas geram pedido de repetição em vez de um cálculo
  possivelmente incorreto;
- respostas mais naturais quando a voz entrega apenas um fragmento;
- espera progressiva após chamado incompleto;
- pausa automática da escuta depois de três chamados consecutivos sem comando,
  impedindo mensagens repetidas indefinidamente.

## Exemplos

```text
você sabe quando tem compromissos esse mês?
como está a agenda desta semana?
abrir esportes pai e tocar as minhas favoritas
criar hábitos para beber água
some para mim mil quatrocentos mais cento e trinta e um
```

Se a escuta pausar após ruído ou três chamados incompletos, basta clicar em
“Escuta contínua” para reativá-la. O contador é zerado ao receber um comando
completo.

## Validação

- 359 testes automatizados aprovados;
- análise Ruff aprovada;
- regressões específicas criadas para todas as frases relatadas;
- nenhum aplicativo real foi aberto nos testes automatizados;
- nenhum dado pessoal foi incluído no Git.
