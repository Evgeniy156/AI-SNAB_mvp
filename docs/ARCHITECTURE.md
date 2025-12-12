# AI-SNAB Architecture (MVP)

**Flow (local & offline):**

Browser UI → FastAPI (`app`) → PostgreSQL (`database`) + MinIO (`storage`) → *(future)* worker(s) → *(future)* local LLM (Ollama)

## Components
- **UI**: Server-rendered pages (`/ui`) + API (`/api`)
- **API**: FastAPI endpoints
- **DB**: PostgreSQL for structured data
- **Object storage**: MinIO (S3-compatible) for files/templates
- **Queue/worker (later)**: background processing (OCR, extraction)
- **LLM (later)**: local Ollama at `OLLAMA_BASE_URL`
