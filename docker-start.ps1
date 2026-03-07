# Quick Start Script for Docker Compose
# Builds and starts all UNOC services

param(
    [switch]$Build,
    [switch]$Stop,
    [switch]$Logs,
    [switch]$Status,
    [string]$Service = ""
)

$ErrorActionPreference = "Stop"

function Show-Usage {
    Write-Host ""
    Write-Host "🚀 UNOC Docker Compose Quick Start" -ForegroundColor Cyan
    Write-Host "=================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Usage:" -ForegroundColor Yellow
    Write-Host "  .\docker-start.ps1              Start all services (or restart if running)"
    Write-Host "  .\docker-start.ps1 -Build       Build images and start"
    Write-Host "  .\docker-start.ps1 -Stop        Stop all services"
    Write-Host "  .\docker-start.ps1 -Status      Show service status"
    Write-Host "  .\docker-start.ps1 -Logs        Follow all logs"
    Write-Host "  .\docker-start.ps1 -Logs -Service batch-service   Follow specific service logs"
    Write-Host ""
    Write-Host "Services:" -ForegroundColor Yellow
    Write-Host "  - postgres (5432)         PostgreSQL database"
    Write-Host "  - traffic-engine (8080)   Traffic simulation"
    Write-Host "  - status-service (50053)  Status propagation"
    Write-Host "  - optical-service (50051) PathFinder (starts FIRST)"
    Write-Host "  - batch-service (50052)   Batch operations (depends on optical)"
    Write-Host "  - backend (5001)          FastAPI REST API"
    Write-Host "  - prometheus (9090)       Metrics collection"
    Write-Host "  - grafana (3000)          Dashboards"
    Write-Host ""
}

function Test-DockerRunning {
    try {
        docker info | Out-Null
        return $true
    } catch {
        Write-Host "❌ ERROR: Docker is not running!" -ForegroundColor Red
        Write-Host "   Please start Docker Desktop and try again." -ForegroundColor Yellow
        return $false
    }
}

function Start-Services {
    param([bool]$BuildImages)
    
    Write-Host ""
    Write-Host "🚀 Starting UNOC services..." -ForegroundColor Cyan
    Write-Host ""
    
    if ($BuildImages) {
        Write-Host "📦 Building Docker images (this may take several minutes)..." -ForegroundColor Yellow
        docker-compose build --parallel
        if ($LASTEXITCODE -ne 0) {
            Write-Host "❌ Build failed!" -ForegroundColor Red
            exit 1
        }
        Write-Host "✅ Build complete!" -ForegroundColor Green
        Write-Host ""
    }
    
    Write-Host "🐳 Starting containers..." -ForegroundColor Yellow
    docker-compose up -d
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Failed to start services!" -ForegroundColor Red
        exit 1
    }
    
    Write-Host ""
    Write-Host "✅ Services started successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "⏳ Waiting for services to be healthy (this may take 30-60 seconds)..." -ForegroundColor Yellow
    Start-Sleep -Seconds 5
    
    # Check service health
    $maxWait = 60
    $waited = 0
    $allHealthy = $false
    
    while ($waited -lt $maxWait -and -not $allHealthy) {
        $status = docker-compose ps --format json | ConvertFrom-Json
        $unhealthy = $status | Where-Object { 
            $_.Health -ne "healthy" -and $_.Service -ne "prometheus" -and $_.Service -ne "grafana" 
        }
        
        if ($unhealthy.Count -eq 0) {
            $allHealthy = $true
        } else {
            Write-Host "   Waiting for: $($unhealthy.Service -join ', ')" -ForegroundColor Gray
            Start-Sleep -Seconds 5
            $waited += 5
        }
    }
    
    Write-Host ""
    if ($allHealthy) {
        Write-Host "✅ All services are healthy!" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Some services may not be ready yet. Check status with: .\docker-start.ps1 -Status" -ForegroundColor Yellow
    }
    
    Write-Host ""
    Write-Host "📊 Service URLs:" -ForegroundColor Cyan
    Write-Host "   Backend:    http://localhost:5001/health" -ForegroundColor White
    Write-Host "   Traffic:    http://localhost:8080/health" -ForegroundColor White
    Write-Host "   Prometheus: http://localhost:9090" -ForegroundColor White
    Write-Host "   Grafana:    http://localhost:3000 (admin/unoc2025)" -ForegroundColor White
    Write-Host ""
    Write-Host "🔍 Next steps:" -ForegroundColor Cyan
    Write-Host "   .\docker-start.ps1 -Status     Check service status"
    Write-Host "   .\docker-start.ps1 -Logs       View all logs"
    Write-Host "   docker-compose logs -f batch-service   View specific service logs"
    Write-Host ""
}

function Stop-Services {
    Write-Host ""
    Write-Host "🛑 Stopping UNOC services..." -ForegroundColor Yellow
    docker-compose down
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Services stopped successfully!" -ForegroundColor Green
    } else {
        Write-Host "❌ Failed to stop services!" -ForegroundColor Red
        exit 1
    }
    Write-Host ""
}

function Show-Status {
    Write-Host ""
    Write-Host "📊 UNOC Service Status" -ForegroundColor Cyan
    Write-Host "=====================" -ForegroundColor Cyan
    Write-Host ""
    
    docker-compose ps
    
    Write-Host ""
    Write-Host "📈 Quick health checks:" -ForegroundColor Cyan
    
    # Test backend
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:5001/health" -UseBasicParsing -TimeoutSec 2
        if ($response.StatusCode -eq 200) {
            Write-Host "   ✅ Backend (5001): OK" -ForegroundColor Green
        }
    } catch {
        Write-Host "   ❌ Backend (5001): Not responding" -ForegroundColor Red
    }
    
    # Test traffic engine
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8080/health" -UseBasicParsing -TimeoutSec 2
        if ($response.StatusCode -eq 200) {
            Write-Host "   ✅ Traffic Engine (8080): OK" -ForegroundColor Green
        }
    } catch {
        Write-Host "   ❌ Traffic Engine (8080): Not responding" -ForegroundColor Red
    }
    
    # Test Prometheus
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:9090/-/healthy" -UseBasicParsing -TimeoutSec 2
        if ($response.StatusCode -eq 200) {
            Write-Host "   ✅ Prometheus (9090): OK" -ForegroundColor Green
        }
    } catch {
        Write-Host "   ❌ Prometheus (9090): Not responding" -ForegroundColor Red
    }
    
    # Test Grafana
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:3000/api/health" -UseBasicParsing -TimeoutSec 2
        if ($response.StatusCode -eq 200) {
            Write-Host "   ✅ Grafana (3000): OK" -ForegroundColor Green
        }
    } catch {
        Write-Host "   ❌ Grafana (3000): Not responding" -ForegroundColor Red
    }
    
    Write-Host ""
}

function Show-Logs {
    param([string]$ServiceName)
    
    Write-Host ""
    if ($ServiceName) {
        Write-Host "📋 Following logs for: $ServiceName" -ForegroundColor Cyan
        Write-Host "   Press Ctrl+C to stop" -ForegroundColor Gray
        Write-Host ""
        docker-compose logs -f $ServiceName
    } else {
        Write-Host "📋 Following logs for all services" -ForegroundColor Cyan
        Write-Host "   Press Ctrl+C to stop" -ForegroundColor Gray
        Write-Host ""
        docker-compose logs -f
    }
}

# Main script
if (-not (Test-DockerRunning)) {
    exit 1
}

if ($Stop) {
    Stop-Services
} elseif ($Status) {
    Show-Status
} elseif ($Logs) {
    Show-Logs -ServiceName $Service
} elseif ($Build) {
    Start-Services -BuildImages $true
} elseif ($args.Count -eq 0 -and -not $PSBoundParameters.Count) {
    Show-Usage
} else {
    Start-Services -BuildImages $false
}
