FROM python:3.11-slim

WORKDIR /app

# Local wheels folder expected at repository root: vendor/wheels
# IMPORTANT:
# - If wheels are Windows-specific (win_amd64), Linux build will ignore them
# - Without --no-index pip can fallback to PyPI and download Linux-compatible wheels
COPY vendor/wheels /wheels
COPY requirements.txt /app/requirements.txt
COPY requirements-dev.txt /app/requirements-dev.txt

RUN pip install --upgrade pip && \
    pip install --prefer-binary --find-links /wheels -r /app/requirements.txt && \
    pip install --prefer-binary --find-links /wheels -r /app/requirements-dev.txt

# Копируем и делаем исполняемым entrypoint скрипт
COPY backend/docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

COPY backend /app/backend
WORKDIR /app/backend

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
