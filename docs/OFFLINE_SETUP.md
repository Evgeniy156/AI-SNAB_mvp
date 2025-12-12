# Offline setup (AI-SNAB)

This project is designed to run **offline** (confidential data stays on your machine).

## 0) Prepare offline artifacts (do this while you still have internet)
### Python wheels
Create a wheelhouse:
```bash
mkdir -p vendor/wheels
pip download -r requirements.txt -d vendor/wheels
pip download -r requirements-dev.txt -d vendor/wheels
```

### Docker images
```bash
docker pull postgres:16
docker pull minio/minio:latest
docker pull redis:7
docker save -o vendor/docker-images.tar postgres:16 minio/minio:latest redis:7
```

On the offline PC:
```bash
docker load -i vendor/docker-images.tar
```

### Static UI files (no CDN)
Place these files into:
`backend/app/static/vendor/`
- bootstrap.min.css
- htmx.min.js

## 1) Local run (Docker Compose)
1) Copy `.env.example` to `.env` and adjust if needed.
2) From `infra/`:
```bash
docker compose -f docker-compose.yml up -d --build
```

## 2) Health checks
- http://localhost:8000/health
- http://localhost:8000/health/db
- http://localhost:8000/health/storage
- http://localhost:8000/ui
