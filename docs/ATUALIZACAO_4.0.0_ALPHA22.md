# Huli 4.0.0-alpha.22

Atualização local de 09/09/2026 para manter a Huli disponível sem ocupar a tela.

## O que mudou

- o painel passa a ter um ícone próprio na bandeja do Windows;
- fechar pelo `X` ou minimizar esconde a janela sem encerrar a Huli;
- o menu do ícone abre o painel, pausa/retoma a escuta e encerra o processo;
- escuta contínua, agenda e temporizadores continuam ativos com o painel oculto;
- lembretes e temporizadores também podem gerar notificações do Windows;
- o painel mostra controles separados para minimizar e encerrar;
- a inicialização minimizada com o Windows pode ser ligada ou desligada no painel;
- instalador e diagnóstico específicos verificam `pystray` e `Pillow`;
- nenhum dado pessoal ou conteúdo do diário foi migrado ou alterado.

## Como usar

Abra normalmente:

```powershell
cd C:\HULI4
.\INICIAR_PAINEL.bat
```

Depois, minimize ou clique no `X`. Procure o ícone azul com a letra **H** perto
do relógio do Windows. Clique duas vezes ou use **Abrir painel**. No menu também
é possível alternar **Escuta contínua** e escolher **Encerrar Huli**.

Para iniciar automaticamente com o Windows, clique em **Inicia com Windows: não**
no topo do painel. O botão muda para **sim**. Também é possível executar:

```powershell
.\CONFIGURAR_INICIO_WINDOWS.bat
```

Para remover:

```powershell
.\REMOVER_INICIO_WINDOWS.bat
```

A configuração usa apenas a área do usuário atual do Windows e não exige conta
de administrador. Ela inicia `painel.py --resident --minimized` com o Python da
`.venv` da própria Huli.

## Segurança e recuperação

- iniciar com o Windows é opt-in: a atualização não ativa isso sozinha;
- comandos de voz que alteram dados continuam sujeitos às confirmações atuais;
- a bandeja não altera as regras do Kernel, do diário ou da sessão;
- se a bandeja não puder ser iniciada, o painel continua utilizável como janela;
- a versão anterior permanece preservada na tag `v4.0.0-alpha.21`.

## Validação

A entrega exige análise Ruff, preflight de instalação/voz/bandeja, suíte completa
de testes e um teste real de abertura e encerramento da interface no Windows.
