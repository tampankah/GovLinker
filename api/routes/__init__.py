from fastapi import APIRouter

from .document_processing import router as document_processing_router
from .chat import router as chat_router

router = APIRouter()

router.include_router(document_processing_router, prefix="/document", tags=["Document Processing"])
router.include_router(chat_router, prefix="/chat", tags=["Chat"])