# Fase 2 — Memory Engine 4.0

## Meta

Criar continuidade persistente entre execuções da Huli sem antecipar Knowledge Graph ou IA híbrida.

## Ordem de construção

1. modelos de memória;
2. política de sensibilidade;
3. repositório SQLite;
4. Memory Engine;
5. captura automática controlada;
6. intenções de memória;
7. MemorySkill;
8. integração no runtime;
9. terminal e API pelo mesmo cérebro;
10. testes e validação ponta a ponta;
11. documentação e merge.

## Critérios obrigatórios

- memória explícita persiste após encerramento;
- tipos `episodic`, `semantic`, `person`, `project`, `preference` e `temporal` são representáveis;
- recall não consulta IA;
- proprietário A não vê memória do proprietário B;
- visitante não acessa memória privada;
- segredo é sempre recusado;
- conteúdo sensível não é aprendido automaticamente;
- candidato automático exige confiança mínima;
- duplicata exata é atualizada em vez de multiplicada;
- esquecimento é lógico e auditável;
- terminal e API usam a mesma Memory Engine;
- regressões das Fases 0 e 1 permanecem verdes.

## Fora de escopo

- Knowledge Graph;
- embeddings/vetores;
- OpenAI/Ollama;
- personalidade avançada;
- servidor central;
- PC Agent;
- voz e visão.

## Gate de conclusão

```text
Huli inicia
→ autentica
→ proprietário registra uma memória
→ memória é persistida
→ outra solicitação recupera a memória
→ API recupera a mesma base
→ segredo é recusado
→ visitante é bloqueado
→ esquecimento desativa a memória
→ CI Windows e Ubuntu aprovam
→ validação local de Rony aprova
```
