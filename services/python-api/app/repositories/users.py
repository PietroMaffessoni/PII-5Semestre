from json import loads
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.core.config import get_settings
from app.core.db import get_connection


def _find_user_with_postgres(usuario: str, senha: str) -> dict | None:
    query = """
        SELECT id, usuario, role
        FROM usuarios
        WHERE usuario = %s
          AND senha = %s
        LIMIT 1
    """

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, (usuario, senha))
            return cursor.fetchone()


def _find_user_with_supabase_rest(usuario: str, senha: str) -> dict | None:
    settings = get_settings()
    query = urlencode(
        {
            "select": "id,usuario,role",
            "usuario": f"eq.{usuario}",
            "senha": f"eq.{senha}",
            "limit": "1",
        }
    )
    request = Request(
        url=f"{settings.supabase_url}/rest/v1/usuarios?{query}",
        headers={
            "apikey": settings.supabase_service_role_key,
            "Authorization": f"Bearer {settings.supabase_service_role_key}",
            "Accept": "application/json",
        },
    )

    with urlopen(request, timeout=10) as response:
        payload = loads(response.read().decode("utf-8"))

    return payload[0] if payload else None


def find_user_by_credentials(usuario: str, senha: str) -> dict | None:
    settings = get_settings()

    if settings.supabase_url and settings.supabase_service_role_key:
        return _find_user_with_supabase_rest(usuario=usuario, senha=senha)

    return _find_user_with_postgres(usuario=usuario, senha=senha)
