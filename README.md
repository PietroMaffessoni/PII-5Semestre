# Automação de Scripts para Visualização de Dados SAP

Projeto de iniciação para a ação **"30 - Criação automatizada de scripts para visualização de dados"**. A proposta e permitir que gestores e analistas descrevam uma necessidade de negócio em linguagem natural e recebam apoio da IA para identificar tabelas SAP relevantes, estruturar os dados necessários e gerar consultas SQL reutilizáveis para consumo no Power BI.

## Objetivo

Reduzir o tempo gasto com solicitações técnicas repetitivas de extração e transformação de dados SAP, aumentando a autonomia do time de negócio e acelerando a construção de dashboards no Power BI.

## Stack planejada

- **Frontend:** Vue 3 + Vite
- **API de aplicação:** Python + FastAPI
- **Pipeline de IA e dados:** Python
- **Banco vetorial e de apoio oficial:** PostgreSQL + pgvector

## Bancos de dados

- **PostgreSQL + pgvector** para embeddings, retrieval, indexação vetorial do dicionário SAP, usuários, login, sessões, histórico de chats, auditoria, feedback e rastreio das consultas SQL geradas.

## Estrutura do repositório

```text
.
├── README.md
├── docs/
│   └── architecture.md
├── data/
│   ├── raw/
│   └── processed/
├── src/                         # frontend Vue na raiz
│   ├── components/
│   ├── data/
│   └── ...
├── index.html
├── vite.config.js
├── package.json
└── services/
    ├── python-ai/
    │   ├── src/
    │   │   ├── connectors/
    │   │   ├── pipelines/
    │   │   └── rag/
    │   └── tests/
    └── python-api/
        └── app/
            ├── api/
            ├── core/
            └── services/
```

## Fluxo funcional esperado

1. O usuário descreve uma pergunta de negócio.
2. A API interpreta a intenção e envia o contexto para o pipeline de IA.
3. O pipeline consulta o dicionário de dados SAP indexado no PostgreSQL com pgvector.
4. A IA retorna tabelas, campos, filtros, joins sugeridos e um rascunho de SQL para uso no Power BI.
5. O frontend apresenta o resultado e permite refinamento, validação e histórico.

## Papel de cada banco

### PostgreSQL + pgvector

- indexação vetorial do dicionário SAP;
- busca semântica de tabelas, campos e descrições técnicas;
- filtros por metadados e joins SQL no mesmo banco;
- cadastro de usuários;
- autenticação e controle de sessão;
- histórico de chats e mensagens;
- armazenamento das consultas SQL geradas;
- feedback humano, aprovação e trilha de auditoria.

## Como rodar

### 1. Frontend Vue

```bash
npm install
npm run dev
```

Build de produção:

```bash
npm run build
```

### 2. API Python

```bash
cd services/python-api
python -m venv venv
source venv/bin/activate (Windows: .\venv\Scripts\Activate.ps1)
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Teste de conexao com o banco:

```bash
cd services/python-api
source venv/bin/activate
python test_db_connection.py
```

### 3. Pipeline de IA

```bash
cd services/python-ai
python -m venv .venv
source .venv/bin/activate (.\.venv\Scripts\Activate.ps1  ; Se estiver no windows)
pip install -r requirements.txt
```
