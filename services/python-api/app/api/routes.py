from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from app.auth.session_store import create_session, get_user_by_token
from app.repositories.users import find_user_by_credentials
from app.services.script_generation import build_script_draft


router = APIRouter()
bearer_scheme = HTTPBearer(auto_error=False)


class LoginRequest(BaseModel):
    usuario: str = Field(..., min_length=1)
    senha: str = Field(..., min_length=1)


class ScriptGenerationRequest(BaseModel):
    question: str = Field(..., min_length=10, description="Pergunta de negócio.")
    context: str | None = Field(default=None, description="Contexto complementar fornecido pelo usuario.")


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
    return draft
