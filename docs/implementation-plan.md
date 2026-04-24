# Plano Tecnico de Implementacao

## Fase 1 - MVP Funcional

Objetivo: entregar o fluxo autenticado `login -> prompt -> interpretacao -> identificacao de tabelas/campos -> SQL inicial`.

### Frontend

- manter rota protegida para o prompt;
- substituir a tela de resultado simples por uma resposta estruturada com:
  - interpretacao da intencao;
  - tabelas relevantes;
  - campos relevantes;
  - joins sugeridos;
  - SQL gerado;
  - recomendacao inicial de visual.

### Backend

- manter autenticacao baseada na tabela `usuarios`;
- criar servico de interpretacao da pergunta do usuario;
- criar servico de consulta ao dicionario SAP ficticio;
- criar gerador de SQL com templates por dominio de negocio;
- devolver uma resposta consolidada para o frontend.

### Banco

- manter PostgreSQL/Supabase para autenticacao e persistencia principal;
- preparar o projeto para `pgvector`, mas no MVP funcional usar o dicionario SAP ficticio local para acelerar a entrega;
- definir script futuro para popular embeddings do dicionario em `pgvector`.

### IA

- usar heuristicas + regras de negocio como primeira camada do MVP;
- extrair:
  - metrica;
  - dimensoes;
  - filtros;
  - periodo;
  - dominio de negocio;
- sugerir visual com base na forma dos dados;
- gerar SQL inicial coerente com o dicionario SAP ficticio.

## Fase 2 - MVP Visual

Objetivo: mostrar a saida final ao usuario de forma visual.

### Frontend

- exibir tabela de pre-visualizacao dos dados;
- renderizar grafico no proprio Vue para validacao rapida;
- permitir refinamento do prompt.

### Backend

- executar apenas SQLs permitidos de forma controlada;
- devolver linhas reais para o frontend;
- armazenar historico de consultas geradas.

### Banco

- popular tabelas transacionais ficticias;
- habilitar `pgvector` e armazenar embeddings do dicionario;
- conectar retrieval semantico ao fluxo de geracao.

### IA

- trocar a busca puramente heuristica por retrieval com `pgvector`;
- melhorar a geracao de SQL com contexto vetorial + regras de validacao.

## Fase 3 - Entrega Final

Objetivo: integrar o resultado com a experiencia final de visualizacao.

### Frontend

- exibir feedback do usuario;
- preparar embed ou export para Power BI.

### Backend

- persistir execucoes;
- adicionar auditoria;
- restringir consultas de forma mais robusta.

### Banco

- consolidar `pgvector` como base vetorial oficial;
- guardar historico, feedback e metricas de uso.

### IA

- melhorar prompts e validacao;
- incluir explicacao da logica usada no SQL;
- sugerir automaticamente o melhor tipo de grafico.

## Ordem de execucao

1. Criar dicionario SAP ficticio estruturado.
2. Implementar interpretacao da pergunta.
3. Implementar identificacao de tabelas/campos.
4. Implementar geracao de SQL inicial.
5. Atualizar frontend para mostrar a resposta estruturada.
6. Validar o MVP funcional.
7. Popular dados ficticios e partir para a camada visual.
