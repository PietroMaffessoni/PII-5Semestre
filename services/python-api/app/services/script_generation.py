from __future__ import annotations

from dataclasses import dataclass
from json import loads
from pathlib import Path
import re


DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "sap_dictionary.json"


@dataclass
class Interpretation:
    domain: str
    metric: str
    dimensions: list[str]
    period_months: int
    filters: list[str]
    chart_suggestion: str


def _load_dictionary() -> dict:
    return loads(DATA_PATH.read_text(encoding="utf-8"))


def _normalize(text: str) -> str:
    replacements = {
        "á": "a",
        "à": "a",
        "ã": "a",
        "â": "a",
        "é": "e",
        "ê": "e",
        "í": "i",
        "ó": "o",
        "ô": "o",
        "õ": "o",
        "ú": "u",
        "ç": "c",
    }
    normalized = text.lower()
    for source, target in replacements.items():
        normalized = normalized.replace(source, target)
    return normalized


def _detect_period_months(question: str) -> int:
    normalized = _normalize(question)
    match = re.search(r"ultim[oa]s?\s+(\d+)\s+mes", normalized)
    if match:
        return int(match.group(1))
    if "ultimo trimestre" in normalized:
        return 3
    if "ultimo semestre" in normalized:
        return 6
    if "ultimo ano" in normalized or "ultimos 12 meses" in normalized:
        return 12
    return 3


def _infer_domain(question: str, dictionary: dict) -> dict:
    normalized = _normalize(question)
    domain_scores: list[tuple[int, dict]] = []

    for domain in dictionary["domains"]:
        score = sum(1 for term in domain["business_terms"] if _normalize(term) in normalized)
        domain_scores.append((score, domain))

    domain_scores.sort(key=lambda item: item[0], reverse=True)
    best_score, best_domain = domain_scores[0]
    if best_score == 0:
        return next(domain for domain in dictionary["domains"] if domain["name"] == "producao")
    return best_domain


def _infer_metric(question: str, domain_name: str) -> str:
    normalized = _normalize(question)
    if domain_name == "faturamento":
        return "valor_faturado" if "valor" in normalized or "receita" in normalized else "quantidade_faturada"
    if domain_name == "compras":
        return "valor_comprado" if "valor" in normalized or "gasto" in normalized else "quantidade_comprada"
    return "volume_producao"


def _infer_dimensions(question: str, domain_name: str) -> list[str]:
    normalized = _normalize(question)
    dimensions: list[str] = []

    if "planta" in normalized:
        dimensions.append("planta")
    if "cliente" in normalized:
        dimensions.append("cliente")
    if "fornecedor" in normalized:
        dimensions.append("fornecedor")
    if "material" in normalized:
        dimensions.append("material")
    if "mes" in normalized or "mensal" in normalized or "ultimos" in normalized:
        dimensions.append("mes")
    if "regional" in normalized or "organizacao de vendas" in normalized:
        dimensions.append("organizacao_vendas")

    if not dimensions:
        defaults = {
            "producao": ["planta", "mes"],
            "faturamento": ["cliente", "mes"],
            "compras": ["fornecedor", "mes"],
        }
        return defaults[domain_name]

    if "mes" not in dimensions:
        dimensions.append("mes")

    return dimensions


def _infer_filters(question: str, dimensions: list[str]) -> list[str]:
    filters = [f"periodo: ultimos meses solicitados"]
    if "planta" in dimensions:
        filters.append("agrupar por planta")
    if "cliente" in dimensions:
        filters.append("agrupar por cliente")
    if "fornecedor" in dimensions:
        filters.append("agrupar por fornecedor")
    return filters


def interpret_question(question: str, dictionary: dict) -> Interpretation:
    domain = _infer_domain(question, dictionary)
    metric = _infer_metric(question, domain["name"])
    dimensions = _infer_dimensions(question, domain["name"])
    period_months = _detect_period_months(question)
    filters = _infer_filters(question, dimensions)

    return Interpretation(
        domain=domain["name"],
        metric=metric,
        dimensions=dimensions,
        period_months=period_months,
        filters=filters,
        chart_suggestion=domain["chart_recommendation"],
    )


def _rank_tables(interpretation: Interpretation, dictionary: dict) -> list[dict]:
    ranked: list[tuple[int, dict]] = []

    for table in dictionary["tables"]:
        score = 0
        if table["domain"] == interpretation.domain:
            score += 5
        score += sum(1 for field in table["fields"] if field["label"] in interpretation.dimensions)
        score += sum(1 for field in table["fields"] if field["label"] == interpretation.metric)
        ranked.append((score, table))

    ranked.sort(key=lambda item: item[0], reverse=True)
    return [item[1] for item in ranked[:3] if item[0] > 0]


def _select_fields(tables: list[dict], interpretation: Interpretation) -> list[dict]:
    relevant_fields: list[dict] = []

    for table in tables:
        for field in table["fields"]:
            if field["label"] == interpretation.metric or field["label"] in interpretation.dimensions:
                relevant_fields.append(
                    {
                        "table": table["name"],
                        "field": field["name"],
                        "label": field["label"],
                        "description": field["description"],
                    }
                )

    seen: set[tuple[str, str]] = set()
    deduplicated = []
    for item in relevant_fields:
        key = (item["table"], item["field"])
        if key not in seen:
            seen.add(key)
            deduplicated.append(item)
    return deduplicated


def _build_join_suggestions(tables: list[dict]) -> list[str]:
    if len(tables) < 2:
        return ["Consulta simples em tabela unica."]

    suggestions = []
    base_table = tables[0]
    for table in tables[1:]:
        shared_keys = sorted(set(base_table["join_keys"]).intersection(table["join_keys"]))
        if shared_keys:
            suggestions.append(
                f"JOIN entre {base_table['name']} e {table['name']} por {', '.join(shared_keys)}."
            )

    return suggestions or ["Relacionamentos sugeridos dependem de validacao manual."]


def _build_sql(interpretation: Interpretation) -> str:
    domain_sql = {
        "producao": {
            "from_clause": "AFKO afko",
            "metric_expr": {
                "volume_producao": "SUM(afko.GAMNG) AS volume_producao",
            },
            "dimension_expr": {
                "planta": "afko.WERKS AS planta",
                "mes": "DATE_TRUNC('month', afko.GSTRP) AS mes",
            },
            "where_date": "afko.GSTRP",
        },
        "faturamento": {
            "from_clause": "VBRK vbrk\nJOIN VBRP vbrp ON vbrk.VBELN = vbrp.VBELN",
            "metric_expr": {
                "valor_faturado": "SUM(vbrp.NETWR) AS valor_faturado",
                "quantidade_faturada": "SUM(vbrp.FKIMG) AS quantidade_faturada",
            },
            "dimension_expr": {
                "cliente": "vbrk.KUNNR AS cliente",
                "organizacao_vendas": "vbrk.VKORG AS organizacao_vendas",
                "material": "vbrp.MATNR AS material",
                "mes": "DATE_TRUNC('month', vbrk.FKDAT) AS mes",
            },
            "where_date": "vbrk.FKDAT",
        },
        "compras": {
            "from_clause": "EKKO ekko\nJOIN EKPO ekpo ON ekko.EBELN = ekpo.EBELN",
            "metric_expr": {
                "valor_comprado": "SUM(ekpo.NETWR) AS valor_comprado",
                "quantidade_comprada": "SUM(ekpo.MENGE) AS quantidade_comprada",
            },
            "dimension_expr": {
                "fornecedor": "ekko.LIFNR AS fornecedor",
                "material": "ekpo.MATNR AS material",
                "mes": "DATE_TRUNC('month', ekko.BEDAT) AS mes",
            },
            "where_date": "ekko.BEDAT",
        },
    }

    template = domain_sql[interpretation.domain]
    select_parts = [template["dimension_expr"][dimension] for dimension in interpretation.dimensions]
    select_parts.append(template["metric_expr"][interpretation.metric])

    group_dimensions = [
        expression.split(" AS ")[0]
        for expression in [template["dimension_expr"][dimension] for dimension in interpretation.dimensions]
    ]

    return (
        "-- SQL inicial gerado a partir do dicionario SAP ficticio\n"
        "SELECT\n  "
        + ",\n  ".join(select_parts)
        + "\nFROM "
        + template["from_clause"]
        + f"\nWHERE {template['where_date']} >= CURRENT_DATE - INTERVAL '{interpretation.period_months} months'"
        + ("\nGROUP BY " + ", ".join(group_dimensions) if group_dimensions else "")
        + ("\nORDER BY " + ", ".join(group_dimensions) if group_dimensions else "")
        + ";"
    )


def build_script_draft(question: str, context: str | None = None) -> dict:
    dictionary = _load_dictionary()
    interpretation = interpret_question(question, dictionary)
    tables = _rank_tables(interpretation, dictionary)
    fields = _select_fields(tables, interpretation)
    joins = _build_join_suggestions(tables)
    sql = _build_sql(interpretation)

    return {
        "question": question,
        "context": context,
        "status": "draft",
        "interpretation": {
            "domain": interpretation.domain,
            "metric": interpretation.metric,
            "dimensions": interpretation.dimensions,
            "period_months": interpretation.period_months,
            "filters": interpretation.filters,
            "chart_suggestion": interpretation.chart_suggestion,
        },
        "suggested_tables": [table["name"] for table in tables],
        "relevant_fields": fields,
        "join_suggestions": joins,
        "suggested_filters": interpretation.filters,
        "draft_script": sql,
    }
