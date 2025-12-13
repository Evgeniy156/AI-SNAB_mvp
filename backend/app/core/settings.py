from pydantic_settings import BaseSettings, SettingsConfigDict
import os


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
        protected_namespaces=("settings_",)
    )

    # Database
    # Use service name in Docker, localhost for local development
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://aisnab:aisnab@database:5432/aisnab"
    )

    # MinIO / S3
    # Use service name in Docker, localhost for local development
    minio_endpoint: str = os.getenv("MINIO_ENDPOINT", "http://minio:9000")
    # Public endpoint for presigned URLs (accessible from browser)
    minio_public_endpoint: str = os.getenv("MINIO_PUBLIC_ENDPOINT", "http://localhost:9000")
    minio_access_key: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    minio_secret_key: str = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    minio_bucket_files: str = os.getenv("MINIO_BUCKET_FILES", "aisnab-files")
    minio_bucket_templates: str = os.getenv("MINIO_BUCKET_TEMPLATES", "aisnab-templates")

    # Redis
    # Use service name in Docker, localhost for local development
    redis_url: str = os.getenv("REDIS_URL", "redis://redis:6379/0")

    # LLM (Ollama)
    # Use service name in Docker, localhost for local development
    ollama_url: str = os.getenv("OLLAMA_URL", "http://ollama:11434")
    chat_model: str = os.getenv("CHAT_MODEL", "qwen2.5:7b-instruct")

    # App
    app_env: str = os.getenv("APP_ENV", "local")
    app_log_level: str = os.getenv("APP_LOG_LEVEL", "INFO")


settings = Settings()
