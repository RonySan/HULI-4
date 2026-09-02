# Huli 4.0.0-alpha.14

Atualização local de 02/09/2026.

## Alterações

- ganho digital de microfone configurável, com padrão de 1,8x e saturação segura;
- criação de compromissos com horários falados em português;
- conclusão de compromisso por número, descrição ou único item do dia;
- painel e terminal iniciados diretamente como proprietário `Rony`;
- autenticação local preservada e reativável por configuração;
- abertura de programas instalados pelo Menu Iniciar e registro do Windows;
- recusa explícita de scripts, URLs, caminhos, parâmetros e sintaxe de terminal.

## Configuração

```text
HULI_VOICE_INPUT_GAIN=1.8
HULI_LOCAL_LOGIN_ENABLED=false
HULI_LOCAL_OWNER_NAME=Rony
```

Para restaurar a tela de login, use `HULI_LOCAL_LOGIN_ENABLED=true`. Essa opção
afeta somente o painel e o terminal locais; a API continua autenticada. O diário
criptografado fica bloqueado no modo sem login e volta a ser aberto pela senha
quando a autenticação local é reativada.

## Exemplos

```text
agenda para amanhã reunião com Paulo às oito horas da manhã
pode concluir esse compromisso de hoje
abrir o Chrome
Huli, abra a calculadora
```

Os dados existentes não são migrados, apagados nem recriados por esta versão.
