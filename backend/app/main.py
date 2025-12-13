from fastapi import FastAPI

from app.core.logging import setup_logging
from app.db.session import engine
from app.api.routers import router as api_router
from app.ui.router import ui_router
from app.services.health import check_db, check_storage
from app.services.storage import ensure_bucket_exists
from app.core.settings import settings

setup_logging()

app = FastAPI(title="AI-SNAB", version="0.1.0")

app.include_router(api_router, prefix="/api")
app.include_router(ui_router)


@app.on_event("startup")
def startup_event():
    """Инициализация при старте приложения: создание бакетов MinIO если нужно."""
    try:
        ensure_bucket_exists(settings.minio_bucket_files)
        ensure_bucket_exists(settings.minio_bucket_templates)
    except Exception as e:
        # Логируем, но не падаем - бакеты создадутся при первой загрузке
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Не удалось создать бакеты MinIO при старте: {e}")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/db")
def health_db():
    try:
        check_db(engine)
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/health/storage")
def health_storage():
    try:
        buckets = check_storage()
        return {"status": "ok", "buckets": buckets}
    except Exception as e:
        return {"status": "error", "error": str(e)}
