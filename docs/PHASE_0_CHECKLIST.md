# Fase 0 — Checklist de Fundação

Objetivo: criar o esqueleto definitivo da Huli sem adicionar inteligência sofisticada antes da hora.

- [x] Estrutura de diretórios oficial
- [x] Kernel mínimo — validado localmente no Windows
- [ ] Sistema de Skills — implementado, aguardando validação final
- [ ] Barramento/eventos internos — implementado, aguardando validação final
- [ ] Configuração centralizada — implementada, aguardando validação final
- [ ] Logging estruturado — implementado, aguardando validação final
- [ ] Persistência/banco inicial — implementado, aguardando validação final
- [ ] API base — implementada, aguardando validação final
- [ ] Autenticação — implementada, aguardando validação final
- [ ] Camada de segurança — implementada, aguardando validação final
- [ ] Padrões de código — implementados, aguardando CI
- [ ] Testes automatizados — implementados, aguardando CI/local
- [ ] Documentação — implementada, aguardando revisão final

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

## Implementação atual — 4.0.0-alpha.2

A branch `phase-0-foundation` contém:

- namespace modular `huli/`
- Kernel mínimo e contratos de request/response
- Skill Registry com fallback controlado
- Foundation Skill de validação
- EventBus síncrono
- configuração centralizada
- logging estruturado
- SQLite com migrações versionadas
- persistência de eventos e interações
- autenticação do proprietário com `scrypt`
- sessões opacas armazenadas por hash
- SecurityPolicy central
- API FastAPI autenticada
- terminal com setup/login na primeira execução
- Ruff como gate de qualidade
- pytest + testes HTTP com HTTPX2/TestClient
- GitHub Actions CI
- documentação da fundação

## Próximo checkpoint

1. CI verde no GitHub.
2. `ruff` e `pytest` verdes no Windows.
3. login local funcionando.
4. `ping` passando pelo Kernel → Skill Registry → FoundationSkill.
5. interação registrada no SQLite.
6. API local respondendo `/health`, login e `/v1/messages` autenticado.

Somente depois desses pontos os itens pendentes serão marcados como concluídos e a Fase 1 poderá começar.
