# Windows PowerShell script to check MinIO credentials
# Usage: powershell -ExecutionPolicy Bypass -File .\tools\minio_creds.ps1

$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$infraPath = Join-Path $scriptPath "..\infra"

Push-Location $infraPath

Write-Host "Checking MinIO credentials in container..."
docker compose exec -T minio sh -lc 'echo "ROOT_USER=$MINIO_ROOT_USER"; echo "ROOT_PASSWORD=$MINIO_ROOT_PASSWORD"'

Pop-Location

