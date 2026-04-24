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
