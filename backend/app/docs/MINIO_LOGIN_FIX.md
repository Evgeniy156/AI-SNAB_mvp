# Быстрое решение проблемы входа в MinIO Console

Если вы видите ошибку "invalid login" в MinIO Console, выполните следующие шаги:

## Шаг 1: Полная очистка и пересоздание MinIO

```powershell
cd infra
docker compose down minio
docker volume rm infra_aisnab_minio_data -f
docker compose up -d minio
```

Подождите **15-20 секунд** после запуска, чтобы MinIO полностью инициализировался.

## Шаг 2: Проверьте креды

```powershell
cd ..
powershell -ExecutionPolicy Bypass -File .\tools\minio_creds.ps1
```

Должно вывести:
```
ROOT_USER=minioadmin
ROOT_PASSWORD=minioadmin
```

## Шаг 3: Вход в Console

1. Откройте **http://localhost:9001** в браузере
2. **Очистите кеш браузера** или откройте в режиме **Инкогнито/Приватный режим**
3. Введите:
   - **Access Key**: `minioadmin`
   - **Secret Key**: `minioadmin`
4. Нажмите **Login**

## Шаг 4: Если все еще не работает

### Вариант A: Проверьте .env файл

Убедитесь, что в корне проекта (не в `infra/`) есть файл `.env`:

```env
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
```

### Вариант B: Принудительно установите креды

Отредактируйте `infra/docker-compose.yml`, секция `minio`:

```yaml
minio:
  environment:
    MINIO_ROOT_USER: minioadmin
    MINIO_ROOT_PASSWORD: minioadmin
```

Затем:
```powershell
cd infra
docker compose down minio
docker volume rm infra_aisnab_minio_data -f
docker compose up -d minio
```

### Вариант C: Используйте другой браузер

Попробуйте открыть Console в другом браузере или в режиме инкогнито.

## Проверка через API

Если вход в Console не работает, но API работает - это нормально. API использует те же креды:

```powershell
curl http://localhost:8080/health/storage
```

Должно вернуть: `{"status":"ok","buckets":[]}`

## Важно

- MinIO требует **15-20 секунд** на инициализацию после первого запуска
- Если volume был создан ранее с другими креды, их нужно сбросить
- Браузер может кешировать старую сессию - используйте режим инкогнито

