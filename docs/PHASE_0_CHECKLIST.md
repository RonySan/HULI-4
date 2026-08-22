# Fase 0 — Checklist de Fundação

Objetivo: criar o esqueleto definitivo da Huli sem adicionar inteligência sofisticada antes da hora.

- [x] Estrutura de diretórios oficial
- [x] Kernel mínimo — validado localmente no Windows
- [ ] Sistema de Skills — implementado, aguardando validação local
- [ ] Barramento/eventos internos — implementado, aguardando validação local
- [ ] Configuração centralizada — implementada, aguardando validação local
- [ ] Logging estruturado — implementado, aguardando validação local
- [ ] Persistência/banco inicial
- [ ] API base
- [ ] Autenticação
- [ ] Camada de segurança
- [ ] Padrões de código
- [ ] Testes automatizados
- [ ] Documentação

## Critério de conclusão

A Fase 0 só termina quando o fluxo abaixo estiver funcionando:

```text
Huli inicia
↓
autentica
↓
recebe mensagem
↓
Kernel interpreta
↓
Skill responde
↓
interação é registrada
```

Depois disso, a versão é testada com o usuário, corrigida, documentada e salva no Git antes da Fase 1.

## Rodada acelerada atual

Implementados na branch `phase-0-foundation`:

- Skill Registry com fallback controlado
- Foundation Skill de validação
- EventBus síncrono
- eventos de entrada e saída do Kernel
- Settings imutável e carregamento por ambiente
- logging centralizado
- bootstrap único de dependências
- testes automatizados específicos para cada componente

Próximo checkpoint: validação local no Windows antes de marcar os quatro módulos como concluídos.
