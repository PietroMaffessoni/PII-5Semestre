def build_script_draft(question: str, context: str | None = None) -> dict:
    return {
        "question": question,
        "context": context,
        "suggested_tables": ["MSEG", "VBRK", "AFKO", "EKPO"],
        "suggested_filters": ["periodo", "planta", "centro de custo"],
        "draft_script": "-- Rascunho inicial\nSELECT *\nFROM sap_table\nWHERE business_filter = 'pending';",
        "status": "draft",
    }
