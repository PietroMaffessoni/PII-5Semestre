from connectors.sap_dictionary import load_dictionary_stub


def retrieve_relevant_tables(question: str) -> list[dict[str, str]]:
    tables = load_dictionary_stub()
    return [
        {
            "table": table.name,
            "description": table.description,
            "module": table.module,
            "match_reason": f"Tabela potencialmente relevante para: {question}",
        }
        for table in tables
    ]


def pgvector_query_stub() -> str:
    return """
    SELECT
      table_name,
      field_name,
      module,
      description
    FROM sap_dictionary_embeddings
    ORDER BY embedding <-> %(embedding)s
    LIMIT 10;
    """
