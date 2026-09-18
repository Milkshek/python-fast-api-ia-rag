from fastapi import APIRouter

from app.documents.routes import documents, processing

router = APIRouter(tags=["Documents"])
for subrouter in (documents.router, processing.router):
    router.include_router(subrouter, prefix="/documents")
