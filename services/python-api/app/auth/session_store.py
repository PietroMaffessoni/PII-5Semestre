from secrets import token_urlsafe


_active_sessions: dict[str, dict] = {}


def create_session(user: dict) -> str:
    token = token_urlsafe(32)
    _active_sessions[token] = user
    return token


def get_user_by_token(token: str) -> dict | None:
    return _active_sessions.get(token)


def remove_session(token: str) -> None:
    _active_sessions.pop(token, None)
