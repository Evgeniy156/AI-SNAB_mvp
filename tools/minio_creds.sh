#!/usr/bin/env bash
# Linux/macOS script to check MinIO credentials
# Usage: bash tools/minio_creds.sh

cd "$(dirname "$0")/../infra" || exit 1

echo "Checking MinIO credentials in container..."
docker compose exec -T minio sh -lc 'echo "ROOT_USER=$MINIO_ROOT_USER"; echo "ROOT_PASSWORD=$MINIO_ROOT_PASSWORD"'

