# Fase 0 — Checklist de Fundação

Objetivo: criar o esqueleto definitivo da Huli sem adicionar inteligência sofisticada antes da hora.

- [ ] Estrutura de diretórios oficial
- [ ] Kernel mínimo
- [ ] Sistema de Skills
- [ ] Barramento/eventos internos
- [ ] Configuração centralizada
- [ ] Logging estruturado
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
