import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.settings import settings
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    return TestClient(app)


@pytest.fixture(scope="function")
def db():
    """
    Database session fixture с транзакционной изоляцией.
    
    Каждый тест выполняется внутри транзакции с SAVEPOINT.
    После теста делается rollback, что гарантирует изоляцию.
    """
    # Создаём engine и connection
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    connection = engine.connect()
    transaction = connection.begin()
    
    # Создаём session, привязанную к connection
    session = Session(bind=connection, autocommit=False, autoflush=False)
    
    # Создаём SAVEPOINT для изоляции внутри теста
    nested = connection.begin_nested()
    
    # Обработчик для пересоздания SAVEPOINT после commit внутри теста
    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(session, transaction):
        if transaction.nested and not transaction._parent.nested:
            # Пересоздаём SAVEPOINT после commit внутри теста
            connection.begin_nested()
    
    # Перехватываем commit и делаем rollback SAVEPOINT вместо commit основной транзакции
    original_commit = session.commit
    
    def patched_commit():
        # Вместо commit основной транзакции, делаем rollback SAVEPOINT и создаём новый
        nonlocal nested
        # Сначала делаем flush, чтобы все изменения попали в SAVEPOINT
        original_flush = session.flush
        original_flush()
        # Затем откатываем SAVEPOINT и создаём новый
        try:
            nested.rollback()
        except Exception:
            pass
        nested = connection.begin_nested()
    
    session.commit = patched_commit
    
    try:
        yield session
    finally:
        # Откатываем SAVEPOINT (все изменения внутри теста)
        try:
            nested.rollback()
        except Exception:
            pass
        # Откатываем основную транзакцию
        transaction.rollback()
        session.close()
        connection.close()

