from fastapi import APIRouter
from .validation_routes import router as validation_router
from .question_routes import router as question_router

router = APIRouter()
router.include_router(validation_router)
router.include_router(question_router)
