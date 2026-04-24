# Arquitetura Inicial

## Visão geral

O projeto foi dividido em três blocos:

- **Frontend Vue** para coleta da necessidade de negócio, visualização do resultado e refinamento da consulta.
- **API Python** como backend principal para orquestrar regras de negocio, chamadas ao pipeline de IA e integração futura com autenticação/auditoria.
- **Camada Python de IA e dados** para ingestão do dicionário SAP, geração de embeddings, retrieval e montagem do contexto que alimenta a geração de SQL.

## Decisão oficial de persistência

- **PostgreSQL + pgvector** será a camada oficial de persistência vetorial e relacional.

### Responsabilidades do PostgreSQL + pgvector

- armazenar embeddings do dicionário SAP;
- indexar chunks, tabelas, campos e descrições técnicas;
- suportar retrieval semântico;
- combinar vetores com filtros e joins SQL;
- Armazenar usuários e dados de autenticação;
- Manter sessões, histórico de chat e mensagens;
- Persistir SQL gerado, feedback, aprovações e logs de auditoria;
- Guardar configurações da aplicação e metadados operacionais.

## Fluxo técnico

1. O frontend envia uma pergunta de negocio.
2. A API normaliza a requisição e chama o pipeline de geração.
3. O pipeline consulta embeddings e metadados do dicionário SAP indexados no PostgreSQL com pgvector.
4. O pipeline combina recuperação semântica com filtros estruturados.
5. A API devolve tabelas sugeridas, campos, filtros, joins, justificativa e rascunho de SQL para uso no Power BI.

## Módulos previstos

### Frontend

- formulário de pergunta de negócio;
- tela de recomendações;
- histórico de execuções;
- feedback humano sobre a resposta.

### API

- healthcheck;
- endpoint de geração de script;
- endpoint de consulta de histórico;
- autenticação e auditoria futuras.

### IA e dados

- conectores SAP;
- normalização de metadados;
- chunking e embeddings;
- retrieval com RAG;
- geração e validação de SQL.
