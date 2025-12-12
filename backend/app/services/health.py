from sqlalchemy import text
from sqlalchemy.engine import Engine
from app.services.storage import list_buckets


def check_db(engine: Engine) -> bool:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return True


def check_storage() -> list[str]:
    return list_buckets()
