from fastapi import APIRouter
from app.api.suppliers import router as suppliers_router
from app.api.cases import router as cases_router
from app.api.document_categories import router as document_categories_router
from app.api.documents import router as documents_router
from app.api.chat import router as chat_router

router = APIRouter()

# Подключаем роутеры
router.include_router(suppliers_router)
router.include_router(cases_router)
router.include_router(document_categories_router)
router.include_router(documents_router)
router.include_router(chat_router)
