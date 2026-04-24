from pgvector.psycopg import register_vector
from psycopg import connect


def create_connection(database_url: str):
    connection = connect(database_url)
    register_vector(connection)
    return connection


def pgvector_bootstrap_sql(dimensions: int = 384) -> str:
    return f"""
    CREATE EXTENSION IF NOT EXISTS vector;

    CREATE TABLE IF NOT EXISTS sap_dictionary_embeddings (
        id BIGSERIAL PRIMARY KEY,
        table_name TEXT NOT NULL,
        field_name TEXT,
        module TEXT NOT NULL,
        description TEXT NOT NULL,
        embedding VECTOR({dimensions}) NOT NULL
    );
    """
