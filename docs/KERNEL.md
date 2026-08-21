# Kernel da Huli

## Objetivo

O Kernel é o núcleo coordenador da Huli. Ele recebe uma mensagem, cria uma requisição estruturada e delega o processamento a um componente que implemente o contrato `KernelHandler`.

Na Fase 0.2, o sistema de Skills ainda não existe. Por isso, quando nenhum handler é conectado, o Kernel devolve uma resposta controlada informando que recebeu a mensagem.

## Responsabilidades

O Kernel pode:

- validar a entrada recebida;
- criar um `request_id` único;
- criar um `KernelRequest`;
- delegar a requisição a um `KernelHandler`;
- validar que a resposta pertence à mesma requisição;
- devolver um `KernelResponse` estruturado.

## O que NÃO pertence ao Kernel

O Kernel não deve conter:

- regras de conversação;
- interpretação de intenção;
- memória;
- banco de dados;
- OpenAI ou Ollama;
- agenda ou tarefas;
- regras de projetos;
- acesso ao Windows;
- voz ou visão;
- lógica específica de Skills.

Essas capacidades entram por módulos próprios nas fases correspondentes do roadmap.

## Contratos

### KernelRequest

Representa uma entrada validada e contém:

- `text`;
- `request_id`;
- `created_at` em UTC.

### KernelResponse

Representa uma resposta estruturada e contém:

- `request_id`;
- `text`;
- `handled_by`;
- `ok`;
- `created_at` em UTC.

### KernelHandler

É um `Protocol` que permite que o próximo componente, como o futuro Skill Registry, seja conectado ao Kernel sem acoplamento direto.

## Regra de correlação

Toda resposta produzida por um handler deve conservar o `request_id` da requisição original. Caso contrário, o Kernel rejeita a resposta.

Essa regra prepara a arquitetura para múltiplos clientes simultâneos, como PC, celular e web.

## Estado desta etapa

Fase 0.2 implementada na branch `phase-0-foundation` e aguardando validação local do usuário antes de ser marcada como concluída.
