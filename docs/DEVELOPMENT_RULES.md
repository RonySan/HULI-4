# Regras de desenvolvimento da Huli

## Branches

- `main`: somente código validado.
- branches de fase: implementação e testes antes do merge.

## Qualidade mínima

Antes de mergear qualquer módulo:

```powershell
python -m ruff check .
python -m pytest
```

## Arquitetura

- Kernel coordena; não contém regras de domínio.
- Skills executam capacidades especializadas.
- Infraestrutura implementa banco, arquivos, rede e logging.
- Security concentra autenticação, autorização e políticas.
- API e clientes são interfaces, não cérebro.
- `bootstrap.py` é o ponto único de composição das dependências concretas.
- Novos recursos entram na fase correta do roadmap.

## Segurança

- nunca versionar `.env`, bancos, tokens, senhas, chaves ou credenciais;
- senhas nunca são armazenadas em texto puro;
- rotas sensíveis exigem autenticação;
- ações de alto risco ganharão confirmação explícita nas fases correspondentes.

## Versionamento

O projeto usa versões progressivas (`alpha`, `beta`, `rc`, estável). Uma nova versão deve representar uma mudança real e validada de capacidade.
