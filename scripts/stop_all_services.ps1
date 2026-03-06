#!/usr/bin/env pwsh
# ==============================================================================
# Stop All Go Services - Force Kill Background Processes
# ==============================================================================
# 
# Kills all Go service processes:
#   1. By exact process name (traffic-engine, optical-service, etc.)
#   2. By port number (:8080, :50051, :50052, :50053, :50054)
#   3. All 'go.exe' processes (build/run processes)
#
# Usage: .\scripts\stop_all_services.ps1
# ==============================================================================

$ErrorActionPreference = "Continue"

function Write-ColorHost {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

function Stop-ProcessByName {
    param(
        [string]$ProcessName,
        [string]$ServiceName
    )
    
    try {
        $processes = Get-Process -Name $ProcessName -ErrorAction SilentlyContinue
        if ($processes) {
            foreach ($proc in $processes) {
                Write-ColorHost "   🔪 Killing $ServiceName (PID $($proc.Id))" -Color Yellow
                Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
            }
            Write-ColorHost "      ✅ Stopped ($($processes.Count) process(es))" -Color Green
        }
        else {
            Write-ColorHost "   ℹ️  $ServiceName - Not running" -Color Gray
        }
    }
    catch {
        Write-ColorHost "   ⚠️  $ServiceName - Error: $_" -Color Red
    }
}

function Stop-ProcessByPort {
    param(
        [int]$Port,
        [string]$ServiceName
    )
    
    try {
        # Find ALL connections on port (not just LISTENING)
        $netstat = netstat -ano | Select-String ":$Port\s"
        
        if ($netstat) {
            $pids = @()
            foreach ($line in $netstat) {
                if ($line -match '\s+(\d+)\s*$') {
                    $pid = $Matches[1]
                    if ($pid -and $pid -ne "0") {
                        $pids += $pid
                    }
                }
            }
            
            $pids = $pids | Select-Object -Unique
            
            if ($pids.Count -gt 0) {
                foreach ($pid in $pids) {
                    try {
                        $process = Get-Process -Id $pid -ErrorAction SilentlyContinue
                        if ($process) {
                            Write-ColorHost "   🔪 Port $Port - Killing PID $pid ($($process.ProcessName))" -Color Yellow
                            Stop-Process -Id $pid -Force -ErrorAction Stop
                        }
                    }
                    catch {
                        # Silent fail (may be already killed by name)
                    }
                }
                Write-ColorHost "      ✅ Port $Port cleaned" -Color Green
            }
            else {
                Write-ColorHost "   ℹ️  Port $Port - No process found" -Color Gray
            }
        }
        else {
            Write-ColorHost "   ℹ️  Port $Port - Not in use" -Color Gray
        }
    }
    catch {
        Write-ColorHost "   ⚠️  Port $Port - Error: $_" -Color Red
    }
}

# ==============================================================================
# Main
# ==============================================================================

Write-ColorHost "`n🛑 Stopping All Go Services..." -Color Cyan
Write-ColorHost "="*70 -Color DarkGray

# Step 1: Kill by exact process name (compiled binaries)
Write-ColorHost "`n[1/3] Stopping compiled service binaries..." -Color Cyan
Stop-ProcessByName -ProcessName "traffic-engine" -ServiceName "Traffic Engine"
Stop-ProcessByName -ProcessName "optical-service" -ServiceName "Optical PathFinder"
Stop-ProcessByName -ProcessName "status-service" -ServiceName "Status Propagation"
Stop-ProcessByName -ProcessName "batch-service" -ServiceName "Batch Operations"
Stop-ProcessByName -ProcessName "port-summary-service" -ServiceName "Port Summary"

# Step 2: Kill all 'go' processes (go run processes)
Write-ColorHost "`n[2/3] Stopping 'go run' processes..." -Color Cyan
try {
    $goProcesses = Get-Process -Name "go" -ErrorAction SilentlyContinue
    if ($goProcesses) {
        Write-ColorHost "   🔪 Killing $($goProcesses.Count) 'go.exe' process(es)" -Color Yellow
        $goProcesses | ForEach-Object { Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue }
        Write-ColorHost "      ✅ Stopped" -Color Green
    }
    else {
        Write-ColorHost "   ℹ️  No 'go.exe' processes found" -Color Gray
    }
}
catch {
    Write-ColorHost "   ⚠️  Error stopping go processes: $_" -Color Red
}

# Step 3: Clean up ports (catch anything missed)
Write-ColorHost "`n[3/3] Cleaning up ports..." -Color Cyan
Stop-ProcessByPort -Port 8080 -ServiceName "Traffic Engine"
Stop-ProcessByPort -Port 50051 -ServiceName "Optical PathFinder"
Stop-ProcessByPort -Port 50053 -ServiceName "Status Propagation"
Stop-ProcessByPort -Port 50052 -ServiceName "Batch Operations"
Stop-ProcessByPort -Port 50054 -ServiceName "Port Summary"

Write-Host ""
Write-ColorHost "="*70 -Color DarkGray
Write-ColorHost "🎉 All Go services stopped!" -Color Green
Write-Host ""
Write-ColorHost "💡 Tip: Close remaining PowerShell windows manually if needed." -Color Gray
Write-Host ""
