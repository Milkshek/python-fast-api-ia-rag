from fastapi import APIRouter

from app.documents.routes import answers, documents, processing, search

router = APIRouter(tags=["Documents"])
for subrouter in (documents.router, processing.router, search.router, answers.router):
    router.include_router(subrouter, prefix="/documents")
