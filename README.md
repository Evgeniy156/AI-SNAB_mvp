AI-SNAB — локальное (offline-first) веб-приложение для сопровождения закупок: ведёт кейсы, поставщиков и документы, помогает контролировать комплектность по чек-листу и готовит основу для автоматизации (OCR → извлечение полей → локальный чат-ассистент).

Сейчас в MVP есть:

Web UI (FastAPI + Jinja2) со страницами /ui/* и чатом справа (drawer)

инфраструктура через Docker Compose (Postgres, MinIO, Redis + приложение)

health-проверки: /health, /health/db, /health/storage

Дальше по плану: CRUD из БД, загрузка/хранение документов в MinIO, OCR-воркер, генерация документов и подключение локальной LLM (Ollama) без утечки данных наружу.

Цель: MVP, который реально помогает в закупках: кейсы, чек-лист, документы, НМЦ/Приложения, локальный ассистент.

## Step 1 — Инфраструктура + Web UI-скелет + smoke tests ✅

### Запуск приложения

```bash
cd infra
docker compose up -d --build
```

### Проверка сервисов

Проверить, что все сервисы видны в compose:
```bash
docker compose config --services
```

Ожидается: `database`, `minio`, `redis`, `app`, `web-proxy`

Проверить статус контейнеров:
```bash
docker compose ps
```

Все контейнеры должны быть в статусе `Running`.

### Доступ к приложению

Приложение доступно через Nginx web-proxy на порту 8080:

- **UI**: http://localhost:8080/ui
- **Health**: http://localhost:8080/health
- **Health DB**: http://localhost:8080/health/db
- **Health Storage**: http://localhost:8080/health/storage

### Запуск smoke tests

**Вариант 1 (внутри контейнера, рекомендуется):**
```bash
docker compose exec app pytest -q
```

**Вариант 2 (локально, если установлены зависимости):**
```bash
cd backend
pytest -q
```

### Чек-лист Step 1

- [x] `docker compose config --services` включает `web-proxy`
- [x] `docker compose ps` показывает `web-proxy` в статусе `Running`
- [x] `curl http://localhost:8080/health` возвращает `{"status":"ok"}`
- [x] `pytest` проходит все smoke tests

### Что реализовано в Step 1

- ✅ Docker Compose: nginx (web-proxy) + postgres + minio + redis + app
- ✅ Web UI (Jinja2): /ui/*, чат справа (drawer)
- ✅ Health endpoints: /health, /health/db, /health/storage
- ✅ Smoke tests pytest: health/ui endpoints

Step 2 — Web UI + реальные данные (Postgres) + CRUD

 SQLAlchemy модели: Supplier, SupplierContact, Case, Document, Template

 Alembic миграции + создание таблиц

 Seed демо-данных (обезличено)

 API CRUD для поставщиков/кейсов/документов/шаблонов

 Web UI: заменить mock на реальные данные из БД

 Тесты CRUD

Step 3 — Документы в Web UI: загрузка, хранение, OCR pipeline

 Web UI: загрузка документов в кейс (pdf/png/jpg/docx)

 Хранение файлов → MinIO (aisnab-files)

 Очередь RabbitMQ + worker (OCR/извлечение полей)

 Web UI: preview + распознанный текст + подтверждение полей

 Тесты storage + worker

Step 4 — Локальный LLM (Ollama) + агент с инструментами

 Установка Ollama локально

 /api/chat → Ollama (без утечки наружу)

 Agent инструменты: validate_case(), generate_doc(), export_zip()

 Guardrails: “не выдумывать факты”

 Тесты поведения ассистента (no-hallucination)

Step 5 — Генерация документов + тестирование перед применением

 Шаблоны docx в MinIO (aisnab-templates)

 Генерация приложений и др.

 Экспорт ZIP (документы + manifest.json + хэши)

 E2E тест: “кейс → 3 КП → НМЦ → export”