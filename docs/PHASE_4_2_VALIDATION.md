# Validação da Fase 4.2 — alpha.12

- Data: 2026-08-27
- Branch: `phase-4-vault-staging`
- Versão: `4.0.0-alpha.12`
- Python local: `3.11.15`
- Schema SQLite: `8`

## Resultado local

```text
Ruff: aprovado
Pytest: 146 aprovados, 0 falhas, 0 avisos
Fase 0: aprovada
Intent Engine: aprovado
Fase 1: aprovada
Fase 2 — Memory Engine: aprovada
Fase 3 — Knowledge Graph staging: aprovada
Fase 4 — Personalidade e Conversação staging: aprovada
Fase 4.1 — Diário Pessoal Privado: aprovada
Fase 4.2 — Cofre Pessoal Seguro: aprovada
```

## Segurança coberta

- ausência de conteúdo, busca, humor e etiquetas legíveis no SQLite/WAL;
- AES-256-GCM com recusa de ciphertext adulterado;
- chave mestra aleatória, scrypt e salt independente;
- camada DPAPI testável no Windows e fallback protegido por senha;
- atualização automática de envelope portátil para proteção do sistema;
- índice cego sem palavras legíveis;
- bloqueio no logout e após inatividade;
- senha errada não abre nem deixa o cofre desbloqueado;
- troca de senha preserva o diário e revoga sessões anteriores;
- senha não pode ser removida enquanto houver entradas;
- migração da alpha.11 com backup anterior, transação e limpeza do SQLite/WAL;
- backup portátil sem conteúdo legível;
- recusa de senha errada e de substituição sem confirmação;
- backup de segurança automático antes da restauração;
- restauração preserva entradas ativas e lixeira;
- backups antigos continuam abrindo com a senha usada na criação.

## CI

- Workflow: [Huli CI #237](https://github.com/RonySan/HULI-4/actions/runs/33107188469)
- Commit remoto validado: `7b5de227f7d9f5f78408ab36db9f057af2baa271`
- Python: `3.11`
- Ubuntu (`ubuntu-latest`): aprovado
- Windows (`windows-latest`): aprovado
- Ruff, 146 testes e validadores das Fases 0 a 4.2: aprovados nos dois sistemas

A `main` permaneceu sem alterações durante o staging.
