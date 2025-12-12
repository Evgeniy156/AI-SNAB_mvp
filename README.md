## План работ (что предстоит сделать дальше)

Ниже — план до MVP, который уже реально помогает в процессе закупок
и контролирует правильность по чек-листу.  

Мы двигаемся по шагам: сделал шаг → фиксируем → следующий шаг.

### Step 1 — Инфраструктура + UI-скелет (сделано / делаем сейчас)
- [x] Docker Compose: nginx + postgres + minio + rabbitmq + redis + app
- [x] UI (Jinja2) + чат справа (drawer) на всех страницах
- [x] /health, /health/db, /health/storage
- [x] офлайн артефакты: wheels, docker-images.tar, bootstrap/htmx

### Step 2 — Реальные данные (Postgres) + CRUD (следующий этап)
- [ ] SQLAlchemy модели: Supplier, SupplierContact, Case, Document, Template
- [ ] Alembic миграции + создание таблиц
- [ ] Seed демо-данных (обезличено) при старте или отдельной командой
- [ ] API CRUD для поставщиков/кейсов/документов
- [ ] UI вместо mock: таблицы из БД + формы добавления (минимум)

### Step 3 — Документы: загрузка, хранение, OCR pipeline (MVP для рутины)
- [ ] Загрузка файлов (pdf/png/jpg) → MinIO (aisnab-files)
- [ ] Статусы обработки: IN_PROGRESS/DONE/ERROR
- [ ] Очередь RabbitMQ + worker (OCR/извлечение полей)
- [ ] Экран “Документы”: preview + распознанный текст + подтверждение полей

### Step 4 — Локальный LLM (Ollama) + агент с инструментами
- [ ] Установка Ollama локально (без облака)
- [ ] Подключение /api/chat к Ollama (без утечки данных наружу)
- [ ] Agent pattern: LLM вызывает инструменты:
      validate_case(), generate_doc(), export_zip()
- [ ] Guardrails: "не выдумывать факты", только из БД/документов

### Step 5 — Генерация документов + тестирование перед применением
- [ ] Шаблоны docx (Прил.7, Прил.7.1, справка-обоснование) в MinIO (aisnab-templates)
- [ ] Генерация docx/pdf из данных кейса + таблиц НМЦ
- [ ] Экспорт ZIP-пакета (все документы + manifest.json)
- [ ] Тесты pytest: health, CRUD, генерация, storage, базовые сценарии
