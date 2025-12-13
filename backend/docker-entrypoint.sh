#!/bin/bash
set -e

echo "Waiting for database to be ready..."
# Ждём доступности PostgreSQL через Python (максимум 30 попыток по 2 секунды = 60 секунд)
max_attempts=30
attempt=0
until python -c "
import sys
sys.path.insert(0, '/app/backend')
from app.core.settings import settings
import psycopg2
from urllib.parse import urlparse
url = urlparse(settings.database_url.replace('postgresql+psycopg2://', 'postgresql://'))
conn = psycopg2.connect(
    host=url.hostname,
    port=url.port or 5432,
    user=url.username,
    password=url.password,
    dbname=url.path[1:]
)
conn.close()
" 2>/dev/null; do
    attempt=$((attempt + 1))
    if [ $attempt -ge $max_attempts ]; then
        echo "Database is not available after 60 seconds"
        exit 1
    fi
    echo "Waiting for database... (attempt $attempt/$max_attempts)"
    sleep 2
done

echo "Database is ready!"

echo "Applying Alembic migrations..."
cd /app/backend
alembic upgrade head

echo "Migrations applied successfully!"

echo "Starting uvicorn..."
exec "$@"

