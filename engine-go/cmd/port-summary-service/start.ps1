# Port Summary Service Startup Script
# Purpose: Start the Port Summary Service with proper environment

param(
    [string]$Port = "50054"
)

Write-Host "🚀 Starting Port Summary Service on port $Port..." -ForegroundColor Cyan

# Check if DATABASE_URL is set
if (-not $env:DATABASE_URL) {
    $env:DATABASE_URL = "postgresql://unoc:unocpw@localhost:5432/unocdb?sslmode=disable"
    Write-Host "⚠️  DATABASE_URL not set, using default: $env:DATABASE_URL" -ForegroundColor Yellow
}

# Set port
$env:PORT = $Port

# Build if needed
$servicePath = ".\port-summary-service.exe"
if (-not (Test-Path $servicePath)) {
    Write-Host "📦 Building service..." -ForegroundColor Yellow
    go build -o port-summary-service.exe .
}

# Check build
if (-not (Test-Path $servicePath)) {
    Write-Host "❌ Build failed!" -ForegroundColor Red
    exit 1
}

# Start service
Write-Host "✅ Starting service..." -ForegroundColor Green
& $servicePath
