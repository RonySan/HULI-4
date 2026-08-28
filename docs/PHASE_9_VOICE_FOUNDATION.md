# Fundação antecipada da Fase 9 — Voz local

Versão de staging: `4.0.0-alpha.13`.

## Decisão

A voz foi antecipada por solicitação do proprietário como uma interface do
terminal. O Kernel, as Skills e as políticas de segurança continuam sendo a
única rota de execução das solicitações reconhecidas.

## Arquitetura

```text
microfone
   ↓
System.Speech local
   ↓
texto reconhecido
   ↓
autenticação e SecurityPolicy
   ↓
Kernel → Intent Engine → Skill
   ↓
resposta textual
   ↓
System.Speech local → alto-falante
```

O backend de voz recebe o texto falado pela entrada padrão do processo. Nenhum
conteúdo do usuário é interpolado em comandos PowerShell. A implementação não
faz chamadas de rede e desativa a voz de forma controlada quando o dispositivo
ou pacote de idioma não está disponível.

## Privacidade e limites

- o reconhecimento só começa após solicitação explícita (`ouvir` ou `modo voz`);
- autenticação e limitações de visitante permanecem ativas;
- respostas de intenções `journal.*` nunca entram na fala automática;
- o modo contínuo termina quando não há fala no período configurado;
- não há palavra de ativação, gravação permanente, identificação biométrica,
  interrupção durante resposta ou XTTS nesta fundação.

## Configuração

```env
HULI_VOICE_AUTO_SPEAK=false
HULI_VOICE_INPUT_TIMEOUT=8
HULI_VOICE_LANGUAGE=pt-BR
HULI_VOICE_RATE=0
HULI_VOICE_VOLUME=100
```

Intervalos aceitos:

- tempo de escuta: 2–60 segundos;
- velocidade: -10 a 10;
- volume: 0–100.

## Validação

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\VALIDAR_VOZ.ps1
```

O validador executa lint, toda a suíte, a fachada de voz com backend isolado,
o bloqueio de fala do diário e as regressões `agendas` e
`o que temos na agenda`.
