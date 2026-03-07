#!/usr/bin/env pwsh
# Quick fix for DB connection pool exhaustion
# Increases pool size from 30 to 100 total connections

Write-Host "🚀 Starting UNOC Backend with INCREASED DB Pool..." -ForegroundColor Cyan
Write-Host ""
Write-Host "📊 Connection Pool Settings:" -ForegroundColor Yellow
Write-Host "   UNOC_DB_POOL_SIZE = 50 (was 10)" -ForegroundColor Green
Write-Host "   UNOC_DB_MAX_OVERFLOW = 50 (was 20)" -ForegroundColor Green
Write-Host "   UNOC_DB_POOL_TIMEOUT = 60 (was 30)" -ForegroundColor Green
Write-Host "   Total Connections: 100 (was 30)" -ForegroundColor Cyan
Write-Host ""

$env:UNOC_DB_POOL_SIZE = "50"
$env:UNOC_DB_MAX_OVERFLOW = "50"
$env:UNOC_DB_POOL_TIMEOUT = "60"
$env:UNOC_ASYNC_MODE = "threading"
$env:UNOC_PORT = "5001"
$env:UNOC_SHUTDOWN_TOKEN = "dev"
$env:UNOC_DEV_FEATURES = "1"
$env:DATABASE_URL = "postgresql+psycopg://unoc:unocpw@localhost:5432/unocdb"
$env:AUTO_ASSIGN_DEFAULT_HARDWARE = "1"
$env:USE_GO_TRAFFIC = "1"

Write-Host "▶️ Starting backend..." -ForegroundColor Green
Write-Host ""

# Activate conda environment and run
conda activate unoc-env
python run.py
