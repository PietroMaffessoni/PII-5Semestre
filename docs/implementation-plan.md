# Plano Tecnico de Implementacao

## Estado atual

O projeto tem um MVP funcional no backend, banco e camada de IA:

- autenticacao backend integrada ao fluxo principal;
- interpretacao inicial da pergunta;
- dicionario SAP ficticio estruturado;
- geracao de SQL inicial por dominio de negocio;
- persistencia do dicionario no Supabase/PostgreSQL;
- embeddings gerados e gravados no banco vetorial;
- retrieval semantico com `pgvector` conectado ao gerador de SQL;
- fallback heuristico mantido como seguranca quando a busca vetorial falhar.

## Fase 1 - MVP Funcional

Objetivo atual: consolidar e validar o fluxo autenticado `login -> prompt -> interpretacao -> retrieval -> identificacao de tabelas/campos -> SQL inicial`.

### Frontend

- alterar a informacao de quando o usuario esta logado de "Logado como admin." para "Logado como pedro - admin.";
- adicionar opcao de admin criar/excluir contas e gerenciar cargo dos usuarios.

### Backend

- validar o fluxo ponta a ponta com cenarios reais de negocio;
- revisar logs e tratamento de erro para identificar quando o retrieval vetorial falha e quando o fallback e acionado.

### Banco

- manter o seed vetorial reaplicavel sem perder embeddings validos;
- validar estrutura, funcao de busca vetorial e consistencia dos dados carregados.

### IA

- calibrar ranking semantico, metricas e dimensoes para reduzir sugestoes irrelevantes;
- revisar heuristicas de apoio para complementar o retrieval semantico.

## Fase 2 - MVP Visual

Objetivo: mostrar a saida final ao usuario com dados reais e validacao rapida.

### Frontend

- exibir tabela de pre-visualizacao dos dados;
- renderizar grafico no proprio Vue para validacao rapida;
- permitir refinamento do prompt.

### Backend

- executar apenas SQLs permitidos de forma controlada;
- devolver linhas reais para o frontend;
- armazenar historico de consultas geradas.

### Banco

- popular tabelas transacionais ficticias para execucao das consultas;
- preparar consultas permitidas e visoes controladas para pre-visualizacao;
- armazenar historico de execucoes.

### IA

- melhorar a geracao de SQL com contexto vetorial + regras de validacao;
- usar o resultado da busca vetorial para justificar melhor as tabelas e campos escolhidos.

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

- guardar historico, feedback e metricas de uso.

### IA

- melhorar prompts e validacao;
- incluir explicacao da logica usada no SQL;
- sugerir automaticamente o melhor tipo de grafico.

## Ordem de execucao restante

1. Validar o MVP funcional com perguntas reais e ajustar ranking/regras onde houver erro.
2. Popular tabelas transacionais ficticias no banco.
3. Implementar execucao controlada do SQL gerado.
4. Devolver linhas reais para o sistema.
5. Armazenar historico das consultas e execucoes.
6. Partir para a camada visual e pre-visualizacao.
