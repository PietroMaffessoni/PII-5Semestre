from psycopg import connect
from psycopg.rows import dict_row
from urllib.request import Request, urlopen

from app.core.config import get_settings


def get_connection():
    settings = get_settings()

    if settings.database_url:
        return connect(conninfo=settings.database_url, row_factory=dict_row)

    return connect(
        host=settings.db_host,
        port=settings.db_port,
        dbname=settings.db_name,
        user=settings.db_user,
        password=settings.db_password,
        sslmode=settings.db_sslmode,
        row_factory=dict_row,
    )


def check_database_connection() -> dict[str, str | int]:
    settings = get_settings()

    if settings.supabase_url and settings.supabase_service_role_key:
        request = Request(
            url=f"{settings.supabase_url}/rest/v1/usuarios?select=id&limit=1",
            headers={
                "apikey": settings.supabase_service_role_key,
                "Authorization": f"Bearer {settings.supabase_service_role_key}",
                "Accept": "application/json",
            },
        )

        with urlopen(request, timeout=10) as response:
            return {"status": "ok", "database_check": response.status}

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 AS ok")
            row = cursor.fetchone()

    return {"status": "ok", "database_check": int(row["ok"])}
