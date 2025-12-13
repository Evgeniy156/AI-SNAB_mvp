"""Service слой для работы с очередью Redis RQ."""
from redis import Redis
from rq import Queue
from app.core.settings import settings


def get_redis_connection() -> Redis:
    """Получить подключение к Redis."""
    # Парсим redis_url (формат: redis://host:port/db)
    # По умолчанию: redis://redis:6379/0
    return Redis.from_url(settings.redis_url, decode_responses=False)


def get_queue(name: str = "default") -> Queue:
    """Получить очередь RQ."""
    conn = get_redis_connection()
    return Queue(name, connection=conn)

