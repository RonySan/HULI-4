# Regras Arquiteturais

Estas regras são permanentes para a linha Huli 4.x, salvo decisão arquitetural formal documentada.

1. **Uma arquitetura, muitas capacidades.** Recursos novos entram como módulos bem definidos; não criamos caminhos paralelos para resolver a mesma responsabilidade.
2. **Kernel coordena.** O núcleo não deve virar um arquivo monolítico de comandos.
3. **Domínios são separados.** Memória, skills, agentes, voz, visão, segurança, integrações e clientes possuem responsabilidades próprias.
4. **Local-first.** Operações simples e dados próprios devem preferir execução local.
5. **IA externa é ferramenta, não fundação.** OpenAI é usada quando raciocínio avançado realmente agrega valor. Fallback local será tratado na fase correspondente.
6. **Memória não inventa fatos.** Recordações devem vir de registros reais e rastreáveis.
7. **Segurança por padrão.** Ações de risco exigem autorização e credenciais nunca entram no repositório.
8. **Compatível com múltiplos clientes.** O cérebro deve poder ser acessado futuramente por PC, celular e web sem duplicar identidade ou memória.
9. **Progressividade.** Uma fase só fecha após implementação, testes, validação do usuário, documentação e Git.
10. **Ideias novas entram no roadmap.** Não mudamos a ordem do projeto por impulso.
