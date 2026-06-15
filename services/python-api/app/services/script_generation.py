from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from json import loads
import logging
from pathlib import Path
import re

from app.core.db import get_connection


logger = logging.getLogger(__name__)
DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "sap_dictionary.json"
DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
WARMUP_QUESTION = "Quero ver o valor faturado por cliente nos ultimos 3 meses"
VALID_INTENT_PATTERNS = (
    r"\b(quero ver|quero analisar|quero acompanhar|quero consultar)\b",
    r"\b(mostre|mostrar|listar|listar me|traga|exiba)\b",
    r"\b(analise|analisar|compare|comparar|resuma|resumir)\b",
)
BUSINESS_CONTEXT_KEYWORDS = (
    "cliente",
    "fornecedor",
    "planta",
    "material",
    "regional",
    "organizacao de vendas",
    "mes",
    "ultimos",
    "trimestre",
    "semestre",
    "ano",
    "faturamento",
    "venda",
    "receita",
    "compra",
    "gasto",
    "producao",
    "ordem",
    "quantidade",
    "valor",
    "volume",
)
HIGH_CONFIDENCE_SIMILARITY = 0.52
MEDIUM_CONFIDENCE_SIMILARITY = 0.40
EXAMPLE_VALID_PROMPTS = (
    "Quero ver o valor faturado por cliente nos ultimos 3 meses",
    "Quero analisar o volume de producao por planta no ultimo trimestre",
    "Mostre o valor comprado por fornecedor nos ultimos 6 meses",
)
REGIONAL_ALIASES = {
    "norte": "NORTE",
    "sul": "SUL",
    "sudeste": "SUDESTE",
    "suleste": "SUDESTE",
    "nordeste": "NORDESTE",
    "centro oeste": "CENTRO-OESTE",
    "centro-oeste": "CENTRO-OESTE",
}


class UnsupportedQuestionError(ValueError):
    pass


@dataclass
class Interpretation:
    domain: str
    metric: str
    dimensions: list[str]
    period_months: int | None
    period_label: str
    filters: list[str]
    chart_suggestion: str
    explicit_year: int | None
    include_current_month: bool
    field_filters: dict[str, str]
    unresolved_filters: list[str]


@dataclass
class RetrievalContext:
    matches: list[dict]
    preferred_domain: str | None
    preferred_tables: set[str]
    preferred_field_refs: set[tuple[str, str]]
    preferred_labels: set[str]


def _load_dictionary() -> dict:
    return loads(DATA_PATH.read_text(encoding="utf-8"))


def _empty_interpretation() -> dict:
    return {
        "domain": None,
        "metric": None,
        "dimensions": [],
        "period_months": None,
        "period_label": None,
        "filters": [],
        "chart_suggestion": None,
        "explicit_year": None,
        "include_current_month": False,
        "field_filters": {},
        "unresolved_filters": [],
    }


def _build_not_understood_message() -> str:
    examples = "; ".join(EXAMPLE_VALID_PROMPTS)
    return (
        "Nao foi possivel compreender sua pergunta com confianca suficiente "
        "ou localizar dados compativeis no dicionario SAP atual. "
        f"Tente reformular usando algo como: {examples}."
    )


def _build_unsupported_filter_message(unresolved_filters: list[str]) -> str:
    unresolved_text = ", ".join(unresolved_filters)
    return (
        "A pergunta foi entendida apenas parcialmente, mas alguns filtros nao puderam ser "
        f"aplicados com seguranca: {unresolved_text}. Reformule a consulta com filtros suportados "
        "ou use codigos e valores existentes no banco ficticio."
    )


@lru_cache(maxsize=1)
def _field_label_map() -> dict[tuple[str, str], str]:
    dictionary = _load_dictionary()
    field_labels: dict[tuple[str, str], str] = {}
    for table in dictionary["tables"]:
        for field in table["fields"]:
            field_labels[(table["name"], field["name"])] = field["label"]
    return field_labels


@lru_cache(maxsize=1)
def _get_embedding_model():
    try:
        from sentence_transformers import SentenceTransformer
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Dependencia ausente: sentence-transformers. "
            "Instale os requisitos do services/python-api para usar retrieval vetorial."
        ) from exc

    return SentenceTransformer(DEFAULT_EMBEDDING_MODEL)


def preload_generation_assets() -> None:
    _load_dictionary()
    _field_label_map()
    _get_embedding_model()


def warmup_vector_search() -> None:
    try:
        _retrieve_vector_matches(WARMUP_QUESTION, limit=3)
        logger.info("Warm-up vetorial concluido.")
    except Exception as exc:
        logger.warning("Warm-up vetorial falhou: %s", exc)


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
    generic_match = re.search(r"\b(\d+)\s+mes(?:es)?(?:\s+atras)?\b", normalized)
    if generic_match:
        return int(generic_match.group(1))
    if "ultimo trimestre" in normalized:
        return 3
    if "ultimo semestre" in normalized:
        return 6
    if "ultimo ano" in normalized or "ultimos 12 meses" in normalized:
        return 12
    return 3


def _detect_explicit_year(question: str) -> int | None:
    normalized = _normalize(question)
    match = re.search(r"\b(?:ano\s+de|em)\s+((?:19|20)\d{2})\b", normalized)
    if match:
        return int(match.group(1))

    bare_year_match = re.search(r"\b((?:19|20)\d{2})\b", normalized)
    if bare_year_match and "ano" in normalized:
        return int(bare_year_match.group(1))

    return None


def _detect_include_current_month(question: str) -> bool:
    normalized = _normalize(question)
    current_month_patterns = (
        "incluindo o mes atual",
        "incluindo mes atual",
        "inclui o mes atual",
        "incluir o mes atual",
        "com o mes atual",
        "contando com o mes atual",
        "considerando o mes atual",
    )
    return any(pattern in normalized for pattern in current_month_patterns)


def _detect_field_filters(question: str) -> tuple[dict[str, str], list[str]]:
    normalized = _normalize(question)
    field_filters: dict[str, str] = {}
    unresolved_filters: list[str] = []

    regional_match = re.search(
        r"\b(?:regional|organizacao de vendas)\s+([a-z]+(?:[ -][a-z]+)?)\b",
        normalized,
    )
    if regional_match:
        regional_key = regional_match.group(1).strip()
        field_filters["organizacao_vendas"] = REGIONAL_ALIASES.get(regional_key, regional_key.upper())
    elif "regional" in normalized or "organizacao de vendas" in normalized:
        unresolved_filters.append("regional/organizacao de vendas")

    pattern_map = {
        "cliente": r"\bcliente\s+(cli-\d+)\b",
        "fornecedor": r"\bfornecedor\s+(for-\d+)\b",
        "material": r"\bmaterial\s+(mat-\d+)\b",
        "planta": r"\bplanta\s+(pl\d+)\b",
    }
    for field_name, pattern in pattern_map.items():
        match = re.search(pattern, normalized)
        if match:
            field_filters[field_name] = match.group(1).upper()

    return field_filters, unresolved_filters


def _build_period_label(
    period_months: int | None,
    explicit_year: int | None,
    include_current_month: bool,
) -> str:
    if explicit_year is not None:
        return f"ano de {explicit_year}"
    if period_months is None:
        return "periodo nao identificado"
    suffix = " incluindo o mes atual" if include_current_month else ""
    return f"ultimos {period_months} meses{suffix}"


def _build_period_where_clause(date_column: str, period_months: int, include_current_month: bool) -> str:
    if include_current_month:
        completed_months_before_current = max(period_months - 1, 0)
        return (
            f"{date_column} >= DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '{completed_months_before_current} months'"
            f"\n  AND {date_column} < DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month'"
        )

    return (
        f"{date_column} >= DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '{period_months} months'"
        f"\n  AND {date_column} < DATE_TRUNC('month', CURRENT_DATE)"
    )


def _retrieve_vector_matches(question: str, limit: int = 8) -> list[dict]:
    from pgvector import Vector

    model = _get_embedding_model()
    vector = Vector(model.encode(question, convert_to_numpy=True, normalize_embeddings=True).tolist())

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    source_key,
                    source_type,
                    table_name,
                    field_name,
                    module,
                    domain_name,
                    description,
                    content_text,
                    similarity
                FROM match_sap_dictionary_embeddings(%s, %s)
                """,
                (vector, limit),
            )
            rows = cursor.fetchall()

    return [dict(row) for row in rows]


def _build_retrieval_context(dictionary: dict, question: str) -> RetrievalContext:
    try:
        matches = _retrieve_vector_matches(question)
    except Exception as exc:
        logger.warning("Falha no retrieval vetorial, usando fallback heuristico: %s", exc)
        return RetrievalContext(
            matches=[],
            preferred_domain=None,
            preferred_tables=set(),
            preferred_field_refs=set(),
            preferred_labels=set(),
        )

    domain_counter = Counter(match["domain_name"] for match in matches if match.get("domain_name"))
    preferred_domain = domain_counter.most_common(1)[0][0] if domain_counter else None
    filtered_matches = [
        match for match in matches if not preferred_domain or match["domain_name"] == preferred_domain
    ]

    preferred_tables: list[str] = []
    preferred_field_refs: set[tuple[str, str]] = set()
    preferred_labels: set[str] = set()
    field_labels = _field_label_map()

    for match in filtered_matches:
        table_name = match["table_name"]
        if table_name not in preferred_tables:
            preferred_tables.append(table_name)

        field_name = match.get("field_name")
        if field_name:
            field_ref = (table_name, field_name)
            preferred_field_refs.add(field_ref)
            label = field_labels.get(field_ref)
            if label:
                preferred_labels.add(label)

    return RetrievalContext(
        matches=filtered_matches,
        preferred_domain=preferred_domain,
        preferred_tables=set(preferred_tables),
        preferred_field_refs=preferred_field_refs,
        preferred_labels=preferred_labels,
    )


def _infer_domain(question: str, dictionary: dict, preferred_domain: str | None = None) -> dict:
    normalized = _normalize(question)
    domain_scores: list[tuple[int, dict]] = []

    for domain in dictionary["domains"]:
        score = sum(1 for term in domain["business_terms"] if _normalize(term) in normalized)
        if preferred_domain == domain["name"]:
            score += 2
        domain_scores.append((score, domain))

    domain_scores.sort(key=lambda item: item[0], reverse=True)
    best_score, best_domain = domain_scores[0]
    if best_score == 0 and preferred_domain:
        return next(domain for domain in dictionary["domains"] if domain["name"] == preferred_domain)
    if best_score == 0:
        return next(domain for domain in dictionary["domains"] if domain["name"] == "producao")
    return best_domain


def _get_domain_match_score(question: str, dictionary: dict) -> int:
    normalized = _normalize(question)
    return max(
        (
            sum(1 for term in domain["business_terms"] if _normalize(term) in normalized)
            for domain in dictionary["domains"]
        ),
        default=0,
    )


def _get_business_signal_score(question: str, dictionary: dict) -> int:
    normalized = _normalize(question)
    score = 0

    for domain in dictionary["domains"]:
        score += sum(1 for term in domain["business_terms"] if _normalize(term) in normalized)

    for table in dictionary["tables"]:
        score += sum(1 for term in table["business_terms"] if _normalize(term) in normalized)
        for field in table["fields"]:
            if _normalize(field["label"]) in normalized:
                score += 1

    score += sum(1 for keyword in BUSINESS_CONTEXT_KEYWORDS if keyword in normalized)
    return score


def _matches_expected_prompt_pattern(question: str) -> bool:
    normalized = _normalize(question)
    has_valid_intent = any(re.search(pattern, normalized) for pattern in VALID_INTENT_PATTERNS)
    has_business_context = any(keyword in normalized for keyword in BUSINESS_CONTEXT_KEYWORDS)
    has_period_hint = any(term in normalized for term in ("ultimos", "mes", "trimestre", "semestre", "ano"))
    return has_valid_intent and (has_business_context or has_period_hint)


def _is_question_understood(question: str, dictionary: dict, retrieval: RetrievalContext) -> bool:
    domain_match_score = _get_domain_match_score(question, dictionary)
    business_signal_score = _get_business_signal_score(question, dictionary)
    top_similarity = 0.0
    average_similarity = 0.0
    if retrieval.matches:
        top_similarity = float(retrieval.matches[0].get("similarity", 0.0))
        average_similarity = sum(float(match.get("similarity", 0.0)) for match in retrieval.matches[:3]) / min(
            len(retrieval.matches),
            3,
        )

    if top_similarity >= HIGH_CONFIDENCE_SIMILARITY:
        return True

    if (
        top_similarity >= MEDIUM_CONFIDENCE_SIMILARITY
        and average_similarity >= 0.34
        and business_signal_score >= 3
        and _matches_expected_prompt_pattern(question)
    ):
        return True

    return domain_match_score >= 2 and business_signal_score >= 4 and _matches_expected_prompt_pattern(question)


def _infer_metric(question: str, domain_name: str, preferred_labels: set[str]) -> str:
    normalized = _normalize(question)

    if domain_name == "faturamento":
        if "valor_faturado" in preferred_labels:
            return "valor_faturado"
        if "quantidade_faturada" in preferred_labels:
            return "quantidade_faturada"
        return "valor_faturado" if "valor" in normalized or "receita" in normalized else "quantidade_faturada"

    if domain_name == "compras":
        if "valor_comprado" in preferred_labels:
            return "valor_comprado"
        if "quantidade_comprada" in preferred_labels:
            return "quantidade_comprada"
        return "valor_comprado" if "valor" in normalized or "gasto" in normalized else "quantidade_comprada"

    return "volume_producao"


def _infer_dimensions(question: str, domain_name: str, preferred_labels: set[str]) -> list[str]:
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
    if "organizacao de vendas" in normalized or "regional" in normalized:
        dimensions.append("organizacao_vendas")

    if "mes" in normalized or "mensal" in normalized or "ultimos" in normalized:
        dimensions.append("mes")

    deduplicated = list(dict.fromkeys(dimensions))
    if not deduplicated:
        defaults = {
            "producao": ["planta", "mes"],
            "faturamento": ["cliente", "mes"],
            "compras": ["fornecedor", "mes"],
        }
        return defaults[domain_name]

    if "mes" not in deduplicated:
        deduplicated.append("mes")

    return deduplicated


def _infer_filters(
    dimensions: list[str],
    *,
    period_months: int | None,
    explicit_year: int | None,
    include_current_month: bool,
    field_filters: dict[str, str],
) -> list[str]:
    if explicit_year is not None:
        filters = [f"periodo: ano de {explicit_year}"]
    elif period_months is not None:
        suffix = " incluindo o mes atual" if include_current_month else ""
        filters = [f"periodo: ultimos {period_months} meses{suffix}"]
    else:
        filters = ["periodo: nao identificado"]

    if "planta" in dimensions:
        filters.append("agrupar por planta")
    if "cliente" in dimensions:
        filters.append("agrupar por cliente")
    if "fornecedor" in dimensions:
        filters.append("agrupar por fornecedor")
    if "material" in dimensions:
        filters.append("agrupar por material")
    for field_name, value in field_filters.items():
        filters.append(f"filtrar por {field_name}: {value}")
    return filters


def interpret_question(question: str, dictionary: dict, retrieval: RetrievalContext) -> Interpretation:
    domain = _infer_domain(question, dictionary, retrieval.preferred_domain)
    metric = _infer_metric(question, domain["name"], retrieval.preferred_labels)
    dimensions = _infer_dimensions(question, domain["name"], retrieval.preferred_labels)
    explicit_year = _detect_explicit_year(question)
    period_months = None if explicit_year is not None else _detect_period_months(question)
    include_current_month = explicit_year is None and _detect_include_current_month(question)
    field_filters, unresolved_filters = _detect_field_filters(question)
    filters = _infer_filters(
        dimensions,
        period_months=period_months,
        explicit_year=explicit_year,
        include_current_month=include_current_month,
        field_filters=field_filters,
    )

    return Interpretation(
        domain=domain["name"],
        metric=metric,
        dimensions=dimensions,
        period_months=period_months,
        period_label=_build_period_label(period_months, explicit_year, include_current_month),
        filters=filters,
        chart_suggestion=domain["chart_recommendation"],
        explicit_year=explicit_year,
        include_current_month=include_current_month,
        field_filters=field_filters,
        unresolved_filters=unresolved_filters,
    )


def _rank_tables(interpretation: Interpretation, dictionary: dict, retrieval: RetrievalContext) -> list[dict]:
    ranked: list[tuple[int, dict]] = []

    for table in dictionary["tables"]:
        score = 0
        if table["domain"] == interpretation.domain:
            score += 5
        if table["name"] in retrieval.preferred_tables:
            score += 6
        score += sum(1 for field in table["fields"] if field["label"] in interpretation.dimensions)
        score += sum(1 for field in table["fields"] if field["label"] == interpretation.metric)
        score += sum(
            2
            for field in table["fields"]
            if (table["name"], field["name"]) in retrieval.preferred_field_refs
        )
        ranked.append((score, table))

    ranked.sort(key=lambda item: item[0], reverse=True)
    return [item[1] for item in ranked[:3] if item[0] > 0]


def _select_fields(tables: list[dict], interpretation: Interpretation, retrieval: RetrievalContext) -> list[dict]:
    relevant_fields: list[dict] = []

    for table in tables:
        for field in table["fields"]:
            is_retrieved_field = (table["name"], field["name"]) in retrieval.preferred_field_refs
            if field["label"] == interpretation.metric or field["label"] in interpretation.dimensions or is_retrieved_field:
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
            "filter_expr": {
                "planta": "afko.WERKS",
            },
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
            "filter_expr": {
                "cliente": "vbrk.KUNNR",
                "organizacao_vendas": "vbrk.VKORG",
                "material": "vbrp.MATNR",
            },
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
            "filter_expr": {
                "fornecedor": "ekko.LIFNR",
                "material": "ekpo.MATNR",
            },
        },
    }

    template = domain_sql[interpretation.domain]
    unresolved_filters = list(interpretation.unresolved_filters)
    supported_dimensions = [
        dimension for dimension in interpretation.dimensions if dimension in template["dimension_expr"]
    ]
    select_parts = [template["dimension_expr"][dimension] for dimension in supported_dimensions]
    select_parts.append(template["metric_expr"][interpretation.metric])

    group_dimensions = [
        expression.split(" AS ")[0]
        for expression in [template["dimension_expr"][dimension] for dimension in supported_dimensions]
    ]

    where_clauses: list[str] = []
    if interpretation.explicit_year is not None:
        where_clauses.append(
            f"DATE_PART('year', {template['where_date']}) = {interpretation.explicit_year}"
        )
    elif interpretation.period_months is not None:
        where_clauses.append(
            _build_period_where_clause(
                template["where_date"],
                interpretation.period_months,
                interpretation.include_current_month,
            )
        )

    for field_name, value in interpretation.field_filters.items():
        filter_expression = template["filter_expr"].get(field_name)
        if not filter_expression:
            unresolved_filters.append(field_name)
            continue

        escaped_value = value.replace("'", "''")
        where_clauses.append(f"UPPER({filter_expression}) = '{escaped_value.upper()}'")

    if unresolved_filters:
        raise UnsupportedQuestionError(_build_unsupported_filter_message(sorted(set(unresolved_filters))))

    return (
        "-- SQL inicial gerado com retrieval vetorial + regras de negocio\n"
        "SELECT\n  "
        + ",\n  ".join(select_parts)
        + "\nFROM "
        + template["from_clause"]
        + "\nWHERE "
        + "\n  AND ".join(where_clauses)
        + ("\nGROUP BY " + ", ".join(group_dimensions) if group_dimensions else "")
        + ("\nORDER BY " + ", ".join(group_dimensions) if group_dimensions else "")
        + ";"
    )


def _serialize_retrieval_matches(matches: list[dict]) -> list[dict]:
    serialized = []
    for match in matches:
        serialized.append(
            {
                "source_type": match["source_type"],
                "table_name": match["table_name"],
                "field_name": match.get("field_name"),
                "module": match["module"],
                "domain_name": match["domain_name"],
                "similarity": round(float(match["similarity"]), 4),
            }
        )
    return serialized


def build_script_draft(question: str, context: str | None = None) -> dict:
    dictionary = _load_dictionary()
    retrieval = _build_retrieval_context(dictionary, question)
    retrieval_mode = "vector" if retrieval.matches else "heuristic_fallback"
    is_understood = _is_question_understood(question, dictionary, retrieval)

    if not is_understood:
        logger.info("Pergunta nao compreendida com confianca suficiente.")
        return {
            "question": question,
            "context": context,
            "status": "not_understood",
            "retrieval_mode": retrieval_mode,
            "is_understood": False,
            "user_message": _build_not_understood_message(),
            "interpretation": _empty_interpretation(),
            "suggested_tables": [],
            "relevant_fields": [],
            "join_suggestions": [],
            "suggested_filters": [],
            "draft_script": "",
            "retrieval_matches": _serialize_retrieval_matches(retrieval.matches[:5]),
        }

    if retrieval_mode == "vector":
        logger.info("Script gerado.")
        print("Script gerado.")
    else:
        logger.info("Fallback acionado.")
        print("Script gerado pelo fallback.")

    interpretation = interpret_question(question, dictionary, retrieval)
    tables = _rank_tables(interpretation, dictionary, retrieval)
    fields = _select_fields(tables, interpretation, retrieval)
    joins = _build_join_suggestions(tables)
    try:
        sql = _build_sql(interpretation)
    except UnsupportedQuestionError as exc:
        logger.info("Pergunta bloqueada por filtro nao aplicavel: %s", exc)
        return {
            "question": question,
            "context": context,
            "status": "not_understood",
            "retrieval_mode": retrieval_mode,
            "is_understood": False,
            "user_message": str(exc),
            "interpretation": _empty_interpretation(),
            "suggested_tables": [],
            "relevant_fields": [],
            "join_suggestions": [],
            "suggested_filters": [],
            "draft_script": "",
            "retrieval_matches": _serialize_retrieval_matches(retrieval.matches[:5]),
        }

    return {
        "question": question,
        "context": context,
        "status": "draft",
        "retrieval_mode": retrieval_mode,
        "is_understood": True,
        "user_message": None,
        "interpretation": {
            "domain": interpretation.domain,
            "metric": interpretation.metric,
            "dimensions": interpretation.dimensions,
            "period_months": interpretation.period_months,
            "period_label": interpretation.period_label,
            "filters": interpretation.filters,
            "chart_suggestion": interpretation.chart_suggestion,
            "explicit_year": interpretation.explicit_year,
            "include_current_month": interpretation.include_current_month,
            "field_filters": interpretation.field_filters,
        },
        "suggested_tables": [table["name"] for table in tables],
        "relevant_fields": fields,
        "join_suggestions": joins,
        "suggested_filters": interpretation.filters,
        "draft_script": sql,
        "retrieval_matches": _serialize_retrieval_matches(retrieval.matches[:5]),
    }
