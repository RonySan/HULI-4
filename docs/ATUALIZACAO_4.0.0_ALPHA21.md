# Huli 4.0.0-alpha.21

Estabilização local de 08/09/2026, construída sobre a alpha.20.

## Objetivo

Melhorar a confiabilidade de abertura e de interpretação sem adicionar novas
áreas de atuação e sem reduzir as proteções das ações por voz.

## Correções

- verificação das dependências principais antes de abrir terminal ou painel;
- diagnóstico específico da voz, do detector Huli/Ruli e dos modelos locais;
- mensagem de reparo compreensível quando a instalação estiver incompleta;
- reconhecimento de Huli, Ruli e Ru-li no começo de comandos comuns;
- reconhecimento de vocativo no fim de consultas, como “que horas são, Huli?”;
- aceitação de pedidos educados, como “você pode abrir a calculadora?”;
- remoção do vocativo do nome do aplicativo antes da busca no Windows;
- preservação de Huli quando o nome for o assunto de memória ou projeto;
- inicialização direta validada no modo proprietário local, sem login.

Palavras ambíguas como “olhe” e “link” continuam proibidas como nome de
ativação. Comandos que alteram dados continuam exigindo a confirmação prevista
pela política de segurança.

## Verificação

Execute `VERIFICAR_HULI.bat` para conferir a instalação e a voz sem abrir a
assistente. A validação da versão inclui testes automatizados, análise Ruff,
inicialização e encerramento reais do terminal.
