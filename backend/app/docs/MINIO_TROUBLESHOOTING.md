# MinIO Troubleshooting

## Проблема: "invalid login" в MinIO Console

Если вы видите ошибку "invalid login" при попытке войти в MinIO Console (http://localhost:9001), выполните следующие шаги:

### 1. Проверьте креды в контейнере

**Windows PowerShell:**
```powershell
powershell -ExecutionPolicy Bypass -File .\tools\minio_creds.ps1
```

**Linux/macOS:**
```bash
bash tools/minio_creds.sh
```

Должно вывести:
```
ROOT_USER=minioadmin
ROOT_PASSWORD=minioadmin
```

### 2. Проверьте .env файл

Убедитесь, что в корне проекта есть файл `.env` с правильными значениями:

```env
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
```

### 3. Пересоздайте контейнер MinIO

Если креды в контейнере не совпадают с `.env`, пересоздайте контейнер:

```bash
cd infra
docker compose down minio
docker compose up -d minio
```

Подождите 5-10 секунд, пока MinIO запустится, затем проверьте креды снова.

### 4. Если проблема сохраняется - сбросьте volume (⚠️ удалит все данные)

**ВНИМАНИЕ:** Это удалит все данные из MinIO (файлы, бакеты).

```bash
cd infra
docker compose down minio
docker volume rm infra_aisnab_minio_data
docker compose up -d minio
```

После этого MinIO создастся заново с креды из `.env`.

### 5. Проверьте вход в Console

Откройте http://localhost:9001 и войдите используя:
- **Access Key**: значение из `MINIO_ACCESS_KEY` (по умолчанию: `minioadmin`)
- **Secret Key**: значение из `MINIO_SECRET_KEY` (по умолчанию: `minioadmin`)

### 6. Проверьте через API

```bash
curl http://localhost:8080/health/storage
```

Должно вернуть `{"status":"ok","buckets":[]}` или список бакетов.

## Частые проблемы

### Проблема: MinIO использует старые креды

**Причина:** MinIO сохраняет креды в volume при первом запуске. Если volume уже существовал с другими креды, они не обновятся автоматически.

**Решение:** Пересоздайте контейнер (шаг 3) или сбросьте volume (шаг 4).

### Проблема: docker-compose не читает .env

**Причина:** Файл `.env` должен быть в корне проекта (рядом с `infra/`), а не в `infra/`.

**Решение:** Убедитесь, что `.env` находится в правильном месте:
```
AI-SNAB_mvp/
  ├── .env          ← здесь
  ├── infra/
  │   └── docker-compose.yml
  └── ...
```

### Проблема: Креды не синхронизированы

**Причина:** `docker-compose.yml` должен использовать `${MINIO_ACCESS_KEY}` и `${MINIO_SECRET_KEY}` для `MINIO_ROOT_USER` и `MINIO_ROOT_PASSWORD`.

**Решение:** Проверьте `infra/docker-compose.yml`:

```yaml
minio:
  environment:
    MINIO_ROOT_USER: ${MINIO_ACCESS_KEY:-minioadmin}
    MINIO_ROOT_PASSWORD: ${MINIO_SECRET_KEY:-minioadmin}
```

Если это не так, обновите файл и пересоздайте контейнер.

