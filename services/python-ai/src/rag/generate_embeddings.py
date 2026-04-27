from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Iterable

try:
    from sentence_transformers import SentenceTransformer
except ModuleNotFoundError as exc:
    raise SystemExit(
        "Dependencia ausente: sentence-transformers. Instale as dependencias com "
        "`python -m pip install -r services/python-ai/requirements.txt`."
    ) from exc
try:
    from dotenv import load_dotenv
except ModuleNotFoundError as exc:
    raise SystemExit(
        "Dependencia ausente: python-dotenv. Instale as dependencias com "
        "`python -m pip install -r services/python-ai/requirements.txt`."
    ) from exc

from vector_store import create_connection


DEFAULT_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
PROJECT_ROOT = Path(__file__).resolve().parents[4]
ENV_PATHS = (
    PROJECT_ROOT / ".env",
    PROJECT_ROOT / "services" / "python-api" / ".env",
)


def _load_environment() -> None:
    for env_path in ENV_PATHS:
        if env_path.exists():
            load_dotenv(env_path, override=False)


def _get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL nao definido. Configure a string de conexao do PostgreSQL/Supabase antes de executar."
        )
    return database_url


def _load_pending_rows(connection, limit: int | None) -> list[tuple[int, str]]:
    query = """
        SELECT id, content_text
        FROM sap_dictionary_embeddings
        WHERE embedding IS NULL
        ORDER BY id
    """
    params: tuple[object, ...] = ()

    if limit is not None:
        query += "\nLIMIT %s"
        params = (limit,)

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        rows = cursor.fetchall()

    return [(int(row[0]), str(row[1])) for row in rows]


def _chunked(values: list[tuple[int, str]], size: int) -> Iterable[list[tuple[int, str]]]:
    for index in range(0, len(values), size):
        yield values[index : index + size]


def generate_embeddings(
    model_name: str = DEFAULT_MODEL_NAME,
    batch_size: int = 32,
    limit: int | None = None,
) -> int:
    _load_environment()
    database_url = _get_database_url()
    connection = create_connection(database_url)

    try:
        rows = _load_pending_rows(connection, limit)
        if not rows:
            print("Nenhum registro pendente encontrado em sap_dictionary_embeddings.")
            return 0

        print(f"Carregando modelo de embeddings: {model_name}")
        model = SentenceTransformer(model_name)

        updated = 0
        for batch in _chunked(rows, batch_size):
            ids = [row_id for row_id, _ in batch]
            texts = [content_text for _, content_text in batch]

            vectors = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)

            with connection.cursor() as cursor:
                for row_id, vector in zip(ids, vectors, strict=True):
                    cursor.execute(
                        """
                        UPDATE sap_dictionary_embeddings
                        SET embedding = %s
                        WHERE id = %s
                        """,
                        (vector.tolist(), row_id),
                    )

            connection.commit()
            updated += len(batch)
            print(f"Lote concluido: {updated}/{len(rows)} embeddings atualizados.")

        return updated
    finally:
        connection.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Gera embeddings reais para os registros da tabela sap_dictionary_embeddings."
    )
    parser.add_argument(
        "--model",
        default=os.getenv("EMBEDDING_MODEL", DEFAULT_MODEL_NAME),
        help=f"Modelo de embeddings. Padrao: {DEFAULT_MODEL_NAME}",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=int(os.getenv("EMBEDDING_BATCH_SIZE", "32")),
        help="Quantidade de registros processados por lote.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limita a quantidade de registros processados nesta execucao.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    updated = generate_embeddings(
        model_name=args.model,
        batch_size=args.batch_size,
        limit=args.limit,
    )
    print(f"Processo finalizado. Total de embeddings gerados: {updated}.")


if __name__ == "__main__":
    main()
