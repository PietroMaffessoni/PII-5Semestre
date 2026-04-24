from fastapi import FastAPI

from app.api.routes import router


app = FastAPI(
    title="SAP Script Generator API",
    version="0.1.0",
    description="API inicial para orquestrar a geracao automatizada de scripts SAP.",
)

app.include_router(router, prefix="/api/v1")


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
