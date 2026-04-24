from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.script_generation import build_script_draft


router = APIRouter()


class ScriptGenerationRequest(BaseModel):
    question: str = Field(..., min_length=10, description="Pergunta de negocio em linguagem natural.")
    context: str | None = Field(default=None, description="Contexto complementar fornecido pelo usuario.")


@router.post("/scripts/generate")
def generate_script(payload: ScriptGenerationRequest) -> dict:
    return build_script_draft(question=payload.question, context=payload.context)
