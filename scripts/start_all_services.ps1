#!/usr/bin/env pwsh
# ==============================================================================
# Start All Go Services - Production Service Orchestrator
# ==============================================================================
# 
# Starts all 5 Go services in separate windows and validates their health:
#   1. Traffic Engine (HTTP :8080)
#   2. Optical PathFinder (gRPC :50051)
#   3. Status Propagation (gRPC :50053)
#   4. Batch Operations (gRPC :50052)
#   5. Port Summary (gRPC :50054)
#
# Each service is validated before proceeding to the next one.
# All services run in minimized PowerShell windows for easy management.
#
# Usage: .\scripts\start_all_services.ps1
# ==============================================================================

param(
    [switch]$SkipValidation = $false  # Skip health checks (for debugging)
)

$ErrorActionPreference = "Stop"
$REPO_ROOT = Split-Path -Parent $PSScriptRoot  # Go up from scripts/ to repo root
$GO_DIR = Join-Path $REPO_ROOT "engine-go"
$MAX_WAIT_SECONDS = 15

# ==============================================================================
# Helper Functions
# ==============================================================================

function Write-ColorHost {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

function Test-GoServiceHealth {
    param(
        [string]$Url,
        [int]$MaxRetries = 15
    )
    
    for ($i = 1; $i -le $MaxRetries; $i++) {
        try {
            $response = Invoke-RestMethod -Uri $Url -TimeoutSec 2 -ErrorAction Stop
            return $true
        }
        catch {
            if ($i -eq $MaxRetries) {
                return $false
            }
            Start-Sleep -Seconds 1
        }
    }
    return $false
}

function Test-GrpcService {
    param(
        [string]$Hostname,
        [int]$Port,
        [int]$MaxRetries = 15
    )
    
    # gRPC health check: try to establish TCP connection
    for ($i = 1; $i -le $MaxRetries; $i++) {
        try {
            $tcpClient = New-Object System.Net.Sockets.TcpClient
            $tcpClient.Connect($Hostname, $Port)
            $tcpClient.Close()
            return $true
        }
        catch {
            if ($i -eq $MaxRetries) {
                return $false
            }
            Start-Sleep -Seconds 1
        }
    }
    return $false
}

# ==============================================================================
# Pre-Flight Checks
# ==============================================================================

Write-ColorHost "`n🚀 Go Services Orchestrator - Starting All Services..." -Color Cyan
Write-ColorHost "=" -Color DarkGray -Repeat 70

# Check if Go is installed
try {
    $goVersion = go version 2>&1
    Write-ColorHost "✅ Go found: $goVersion" -Color Green
}
catch {
    Write-ColorHost "❌ Go not found! Please install Go 1.21+." -Color Red
    exit 1
}

# Check if engine-go directory exists
if (-not (Test-Path $GO_DIR)) {
    Write-ColorHost "❌ Directory '$GO_DIR' not found!" -Color Red
    Write-ColorHost "   Expected: $GO_DIR" -Color Yellow
    Write-ColorHost "   Current:  $(Get-Location)" -Color Yellow
    exit 1
}

# ==============================================================================
# Service 1: Traffic Engine (HTTP :8080)
# ==============================================================================

Write-ColorHost "`n[1/4] Starting Traffic Engine (HTTP :8080)..." -Color Cyan

$trafficCmd = "Set-Location '$GO_DIR'; go run ./cmd/traffic-engine"
Start-Process pwsh -ArgumentList "-NoExit", "-Command", $trafficCmd -WindowStyle Minimized

if (-not $SkipValidation) {
    Write-Host "   ⏳ Waiting for Traffic Engine to be ready..." -NoNewline
    if (Test-GoServiceHealth -Url "http://localhost:8080/health") {
        Write-ColorHost " ✅ READY" -Color Green
    }
    else {
        Write-ColorHost " ❌ FAILED (timeout after ${MAX_WAIT_SECONDS}s)" -Color Red
        Write-ColorHost "   💡 Check the Traffic Engine window for errors." -Color Yellow
        exit 1
    }
}

# ==============================================================================
# Service 2: Optical PathFinder (gRPC :50051)
# ==============================================================================

Write-ColorHost "`n[2/4] Starting Optical PathFinder (gRPC :50051)..." -Color Cyan

$opticalCmd = "Set-Location '$GO_DIR'; go run ./cmd/optical-service"
Start-Process pwsh -ArgumentList "-NoExit", "-Command", $opticalCmd -WindowStyle Minimized

if (-not $SkipValidation) {
    Write-Host "   ⏳ Waiting for Optical PathFinder to be ready..." -NoNewline
    if (Test-GrpcService -Hostname "localhost" -Port 50051) {
        Write-ColorHost " ✅ READY" -Color Green
    }
    else {
        Write-ColorHost " ❌ FAILED (timeout after ${MAX_WAIT_SECONDS}s)" -Color Red
        Write-ColorHost "   💡 Check the Optical PathFinder window for errors." -Color Yellow
        exit 1
    }
}

# ==============================================================================
# Service 3: Status Propagation (gRPC :50053)
# ==============================================================================

Write-ColorHost "`n[3/4] Starting Status Propagation (gRPC :50053)..." -Color Cyan

$statusCmd = "Set-Location '$GO_DIR'; go run ./cmd/status-service"
Start-Process pwsh -ArgumentList "-NoExit", "-Command", $statusCmd -WindowStyle Minimized

if (-not $SkipValidation) {
    Write-Host "   ⏳ Waiting for Status Propagation to be ready..." -NoNewline
    if (Test-GrpcService -Hostname "localhost" -Port 50053) {
        Write-ColorHost " ✅ READY" -Color Green
    }
    else {
        Write-ColorHost " ❌ FAILED (timeout after ${MAX_WAIT_SECONDS}s)" -Color Red
        Write-ColorHost "   💡 Check the Status Propagation window for errors." -Color Yellow
        exit 1
    }
}

# ==============================================================================
# Service 4: Batch Operations (gRPC :50052)
# ==============================================================================

Write-ColorHost "`n[4/5] Starting Batch Operations (gRPC :50052)..." -Color Cyan

$batchCmd = "Set-Location '$GO_DIR'; go run ./cmd/batch-service"
Start-Process pwsh -ArgumentList "-NoExit", "-Command", $batchCmd -WindowStyle Minimized

if (-not $SkipValidation) {
    Write-Host "   ⏳ Waiting for Batch Operations to be ready..." -NoNewline
    if (Test-GrpcService -Hostname "localhost" -Port 50052) {
        Write-ColorHost " ✅ READY" -Color Green
    }
    else {
        Write-ColorHost " ❌ FAILED (timeout after ${MAX_WAIT_SECONDS}s)" -Color Red
        Write-ColorHost "   💡 Check the Batch Operations window for errors." -Color Yellow
        exit 1
    }
}

# ==============================================================================
# Service 5: Port Summary (gRPC :50054)
# ==============================================================================

Write-ColorHost "`n[5/5] Starting Port Summary (gRPC :50054)..." -Color Cyan

$portSummaryCmd = "Set-Location '$GO_DIR/cmd/port-summary-service'; `$env:DATABASE_URL='postgresql://unoc:unocpw@localhost:5432/unocdb?sslmode=disable'; `$env:PORT='50054'; go run ."
Start-Process pwsh -ArgumentList "-NoExit", "-Command", $portSummaryCmd -WindowStyle Minimized

if (-not $SkipValidation) {
    Write-Host "   ⏳ Waiting for Port Summary to be ready..." -NoNewline
    if (Test-GrpcService -Hostname "localhost" -Port 50054) {
        Write-ColorHost " ✅ READY" -Color Green
    }
    else {
        Write-ColorHost " ❌ FAILED (timeout after ${MAX_WAIT_SECONDS}s)" -Color Red
        Write-ColorHost "   💡 Check the Port Summary window for errors." -Color Yellow
        exit 1
    }
}

# ==============================================================================
# Summary
# ==============================================================================

Write-ColorHost "`n" + "="*70 -Color DarkGray
Write-ColorHost "🎉 ALL SERVICES STARTED SUCCESSFULLY!" -Color Green
Write-ColorHost "="*70 -Color DarkGray

Write-Host "`n📊 Service Status:"
Write-ColorHost "   ✅ Traffic Engine       → http://localhost:8080" -Color Green
Write-ColorHost "   ✅ Optical PathFinder   → grpc://localhost:50051" -Color Green
Write-ColorHost "   ✅ Status Propagation   → grpc://localhost:50053" -Color Green
Write-ColorHost "   ✅ Batch Operations     → grpc://localhost:50052" -Color Green
Write-ColorHost "   ✅ Port Summary         → grpc://localhost:50054" -Color Green

Write-Host "`n💡 Next Steps:"
Write-Host "   1. Start Python Backend: " -NoNewline
Write-ColorHost "conda activate unoc-env && python run.py" -Color Cyan
Write-Host "   2. Start Frontend:       " -NoNewline
Write-ColorHost "cd unoc-frontend-v2; npm run dev" -Color Cyan
Write-Host "   3. Open Browser:         " -NoNewline
Write-ColorHost "http://localhost:5173" -Color Cyan

Write-Host "`n🛑 To stop all services: Close all PowerShell windows or press Ctrl+C in each."
Write-Host ""
