from fastapi import FastAPI

from app.documents.router import router as documents_router

app = FastAPI(title="Document Intelligence Assistant")
app.include_router(documents_router)


@app.get("/health", tags=["Infrastructure"])
async def health() -> dict[str, str]:
    """Indique que le serveur HTTP répond ; ne vérifie pas PostgreSQL."""
    return {"status": "ok"}
