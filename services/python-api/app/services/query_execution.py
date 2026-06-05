from __future__ import annotations

from dataclasses import dataclass
from json import dumps
import re

from psycopg import sql

from app.core.db import get_connection


MAX_PREVIEW_ROWS = 100
ALLOWED_TABLES = {"afko", "afpo", "vbrk", "vbrp", "ekko", "ekpo"}
MONTH_LABELS = {
    "01": "Janeiro",
    "02": "Fevereiro",
    "03": "Marco",
    "04": "Abril",
    "05": "Maio",
    "06": "Junho",
    "07": "Julho",
    "08": "Agosto",
    "09": "Setembro",
    "10": "Outubro",
    "11": "Novembro",
    "12": "Dezembro",
}
FORBIDDEN_SQL_TOKENS = (
    " insert ",
    " update ",
    " delete ",
    " drop ",
    " truncate ",
    " alter ",
    " create ",
    " grant ",
    " revoke ",
    " comment ",
    " execute ",
    " call ",
    " copy ",
)


@dataclass
class QueryExecutionResult:
    rows: list[dict]
    row_count: int
    status: str


def _normalize_sql(generated_sql: str) -> str:
    sql_text = generated_sql.strip()
    sql_text = re.sub(r"^--.*?$", "", sql_text, flags=re.MULTILINE).strip()
    return sql_text.rstrip(";").strip()


def validate_generated_sql(generated_sql: str) -> str:
    sql_text = _normalize_sql(generated_sql)
    lowered = f" {sql_text.lower()} "

    if not re.match(r"^\s*(select|with)\b", sql_text, flags=re.IGNORECASE):
        raise ValueError("Apenas consultas SELECT sao permitidas.")

    if ";" in sql_text:
        raise ValueError("A consulta deve conter apenas uma instrucao SQL.")

    for token in FORBIDDEN_SQL_TOKENS:
        if token in lowered:
            raise ValueError("A consulta contem comandos nao permitidos.")

    used_tables = set(re.findall(r"\b(?:from|join)\s+([a-zA-Z_][a-zA-Z0-9_]*)", lowered))
    if not used_tables:
        raise ValueError("Nao foi possivel identificar tabelas na consulta gerada.")

    disallowed_tables = used_tables.difference(ALLOWED_TABLES)
    if disallowed_tables:
        raise ValueError(
            "A consulta referencia tabelas nao autorizadas: " + ", ".join(sorted(disallowed_tables))
        )

    return sql_text


def execute_preview_query(generated_sql: str, row_limit: int = MAX_PREVIEW_ROWS) -> QueryExecutionResult:
    safe_sql = validate_generated_sql(generated_sql)
    limit = min(max(row_limit, 1), MAX_PREVIEW_ROWS)
    wrapped_query = sql.SQL(
        "WITH generated_query AS ({query}) SELECT * FROM generated_query LIMIT %s"
    ).format(query=sql.SQL(safe_sql))

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(wrapped_query, (limit,))
            rows = [dict(row) for row in cursor.fetchall()]

    return QueryExecutionResult(
        rows=rows,
        row_count=len(rows),
        status="executed",
    )


def _format_chart_label(column: str, value) -> str:
    if value is None:
        return ""

    if column == "mes":
        match = re.match(r"^(\d{4})-(\d{2})-", str(value))
        if match:
            _, month = match.groups()
            return MONTH_LABELS.get(month, str(value))

    return str(value)


def build_chart_payload(rows: list[dict]) -> dict | None:
    if not rows:
        return None

    columns = list(rows[0].keys())
    numeric_columns = [
        column
        for column in columns
        if all(row.get(column) is not None and not isinstance(row.get(column), bool) and _is_number(row.get(column)) for row in rows)
    ]
    dimension_columns = [column for column in columns if column not in numeric_columns]

    category_column = "mes" if "mes" in dimension_columns else (dimension_columns[0] if dimension_columns else None)
    value_column = numeric_columns[0] if numeric_columns else None

    if not category_column or not value_column:
        return None

    chart_type = "line" if category_column == "mes" else "bar"
    labels = [_format_chart_label(category_column, row.get(category_column)) for row in rows]
    values = [float(row.get(value_column, 0)) for row in rows]

    return {
        "chart_type": chart_type,
        "category_column": category_column,
        "value_column": value_column,
        "labels": labels,
        "values": values,
        "value_format": "currency" if "valor" in value_column.lower() else "number",
    }


def _is_number(value) -> bool:
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def save_query_history(
    *,
    user: dict,
    question: str,
    generated_sql: str,
    retrieval_mode: str,
    execution_status: str,
    rows: list[dict] | None = None,
) -> None:
    preview_rows = rows or []
    query = """
        INSERT INTO script_query_history (
            user_id,
            requested_by,
            question,
            generated_sql,
            retrieval_mode,
            execution_status,
            row_count,
            result_preview
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
    """

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                query,
                (
                    user.get("id"),
                    user["usuario"],
                    question,
                    generated_sql,
                    retrieval_mode,
                    execution_status,
                    len(preview_rows),
                    dumps(preview_rows, ensure_ascii=True, default=str),
                ),
            )
        connection.commit()


def list_query_history(limit: int = 20) -> list[dict]:
    query = """
        SELECT
            id,
            user_id,
            requested_by,
            question,
            generated_sql,
            retrieval_mode,
            execution_status,
            row_count,
            result_preview,
            created_at
        FROM script_query_history
        ORDER BY created_at DESC
        LIMIT %s
    """

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, (limit,))
            return [dict(row) for row in cursor.fetchall()]
