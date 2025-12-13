"""Service слой для работы с MinIO/S3 хранилищем."""
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from app.core.settings import settings


def get_s3_client():
    """Получить S3 клиент для MinIO."""
    return boto3.client(
        "s3",
        endpoint_url=settings.minio_endpoint,
        aws_access_key_id=settings.minio_access_key,
        aws_secret_access_key=settings.minio_secret_key,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


def list_buckets() -> list[str]:
    """Получить список бакетов."""
    s3 = get_s3_client()
    resp = s3.list_buckets()
    return [b["Name"] for b in resp.get("Buckets", [])]


def ensure_bucket_exists(bucket_name: str) -> None:
    """Убедиться что бакет существует, создать если нет."""
    s3 = get_s3_client()
    try:
        s3.head_bucket(Bucket=bucket_name)
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        if error_code == "404" or error_code == "NoSuchBucket":
            # Создаем бакет
            s3.create_bucket(Bucket=bucket_name)
        else:
            raise


def upload_file(bucket_name: str, storage_key: str, file_content: bytes, content_type: str | None = None) -> None:
    """Загрузить файл в MinIO."""
    s3 = get_s3_client()
    extra_args = {}
    if content_type:
        extra_args["ContentType"] = content_type
    s3.put_object(Bucket=bucket_name, Key=storage_key, Body=file_content, **extra_args)


def presigned_get_url(bucket_name: str, storage_key: str, expires: int = 3600) -> str:
    """Получить presigned URL для скачивания файла."""
    s3 = get_s3_client()
    url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket_name, "Key": storage_key},
        ExpiresIn=expires
    )
    # Заменяем внутренний endpoint на публичный для доступа из браузера
    if settings.minio_endpoint != settings.minio_public_endpoint:
        url = url.replace(settings.minio_endpoint, settings.minio_public_endpoint)
    return url


def get_file(bucket_name: str, storage_key: str) -> bytes:
    """Получить файл из MinIO."""
    s3 = get_s3_client()
    response = s3.get_object(Bucket=bucket_name, Key=storage_key)
    return response['Body'].read()
