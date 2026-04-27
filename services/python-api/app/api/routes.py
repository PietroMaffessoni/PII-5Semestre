from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from app.auth.session_store import create_session, get_user_by_token
from app.repositories.users import find_user_by_credentials
from app.services.query_execution import (
    execute_preview_query,
    list_query_history,
    save_query_history,
)
from app.services.script_generation import build_script_draft


router = APIRouter()
bearer_scheme = HTTPBearer(auto_error=False)


class LoginRequest(BaseModel):
    usuario: str = Field(..., min_length=1)
    senha: str = Field(..., min_length=1)


class ScriptGenerationRequest(BaseModel):
    question: str = Field(..., min_length=10, description="Pergunta de negócio.")
    context: str | None = Field(default=None, description="Contexto complementar fornecido pelo usuario.")
    execute: bool = Field(default=False, description="Executa a consulta gerada de forma controlada.")
    preview_limit: int = Field(default=20, ge=1, le=100, description="Limite maximo de linhas retornadas.")


def filter_script_response_by_role(draft: dict, role: str | None) -> dict:
    if role == "admin":
        return draft

    return {
        "question": draft["question"],
        "context": draft.get("context"),
        "status": draft["status"],
        "requested_by": draft.get("requested_by"),
        "preview_rows": draft.get("preview_rows", []),
        "preview_row_count": draft.get("preview_row_count", 0),
    }


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticacao obrigatoria.",
        )

    user = get_user_by_token(credentials.credentials)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessao invalida ou expirada.",
        )

    return user


@router.post("/auth/login")
def login(payload: LoginRequest) -> dict:
    user = find_user_by_credentials(usuario=payload.usuario, senha=payload.senha)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario ou senha invalidos.",
        )

    token = create_session(user)
    return {"token": token, "user": user}


@router.get("/auth/me")
def me(current_user: dict = Depends(get_current_user)) -> dict:
    return {"user": current_user}


@router.post("/scripts/generate")
def generate_script(
    payload: ScriptGenerationRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    draft = build_script_draft(question=payload.question, context=payload.context)
    draft["requested_by"] = current_user["usuario"]

    execution_status = "draft_only"
    preview_rows: list[dict] = []
    if payload.execute:
        try:
            execution = execute_preview_query(draft["draft_script"], row_limit=payload.preview_limit)
        except ValueError as exc:
            execution_status = "blocked"
            save_query_history(
                user=current_user,
                question=payload.question,
                generated_sql=draft["draft_script"],
                retrieval_mode=draft["retrieval_mode"],
                execution_status=execution_status,
                rows=[],
            )
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

        execution_status = execution.status
        preview_rows = execution.rows
        draft["preview_rows"] = execution.rows
        draft["preview_row_count"] = execution.row_count

    save_query_history(
        user=current_user,
        question=payload.question,
        generated_sql=draft["draft_script"],
        retrieval_mode=draft["retrieval_mode"],
        execution_status=execution_status,
        rows=preview_rows,
    )

    return filter_script_response_by_role(draft, current_user.get("role"))


@router.get("/scripts/history")
def get_script_history(
    limit: int = 20,
    current_user: dict = Depends(get_current_user),
) -> dict:
    history = list_query_history(limit=limit)
    return {
        "requested_by": current_user["usuario"],
        "items": history,
    }
