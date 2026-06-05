from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.db import check_database_connection
from app.core.config import get_settings
from app.services.script_generation import preload_generation_assets, warmup_vector_search

settings = get_settings()

app = FastAPI(
    title="SAP Script Generator API",
    version="0.1.0",
    description="API para autenticacao e geracao inicial de SQL para Power BI.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")


@app.on_event("startup")
def startup_warmup() -> None:
    preload_generation_assets()
    warmup_vector_search()


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/db")
def database_healthcheck() -> dict[str, str | int]:
    try:
        return check_database_connection()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Falha na conexao com o banco: {exc}") from exc
