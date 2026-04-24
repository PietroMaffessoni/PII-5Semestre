def build_script_draft(question: str, context: str | None = None) -> dict:
    return {
        "question": question,
        "context": context,
        "suggested_tables": ["MSEG", "VBRK", "AFKO", "EKPO"],
        "suggested_filters": ["periodo", "planta", "centro de custo"],
        "draft_script": (
            "-- Rascunho inicial para Power BI\n"
            "SELECT\n"
            "  planta,\n"
            "  DATE_TRUNC('month', data_referencia) AS mes,\n"
            "  SUM(volume_producao) AS volume_total\n"
            "FROM sap_table\n"
            "WHERE data_referencia >= CURRENT_DATE - INTERVAL '3 months'\n"
            "GROUP BY planta, DATE_TRUNC('month', data_referencia)\n"
            "ORDER BY mes, planta;"
        ),
        "status": "draft",
    }
