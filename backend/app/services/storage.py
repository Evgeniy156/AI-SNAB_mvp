import boto3
from botocore.config import Config
from app.core.settings import settings


def get_s3_client():
    # MinIO is S3-compatible
    return boto3.client(
        "s3",
        endpoint_url=settings.minio_endpoint,
        aws_access_key_id=settings.minio_access_key,
        aws_secret_access_key=settings.minio_secret_key,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


def list_buckets() -> list[str]:
    s3 = get_s3_client()
    resp = s3.list_buckets()
    return [b["Name"] for b in resp.get("Buckets", [])]
