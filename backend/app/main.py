from fastapi import FastAPI

from app.core.logging import setup_logging
from app.db.session import engine
from app.api.routers import router as api_router
from app.ui.router import ui_router
from app.services.health import check_db, check_storage

setup_logging()

app = FastAPI(title="AI-SNAB", version="0.1.0")

app.include_router(api_router, prefix="/api")
app.include_router(ui_router)


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
