import sys
from pathlib import Path
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Добавляем путь к проекту для импорта модулей
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Импорт настроек и моделей
from app.core.settings import settings
from app.db.base import Base
import app.models  # Импорт всех моделей для регистрации в Base.metadata

config = context.config
# Пропускаем fileConfig, так как в alembic.ini нет секций логирования

# Используем database_url из настроек
config.set_main_option("sqlalchemy.url", settings.database_url)

# Указываем metadata для генерации миграций
target_metadata = Base.metadata

def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    # Используем database_url из настроек напрямую
    connectable = engine_from_config(
        {"sqlalchemy.url": settings.database_url},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
