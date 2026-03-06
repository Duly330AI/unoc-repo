# Stop Go Traffic Engine gracefully

$pidFile = "C:\noc_project\UNOC\unoc\engine-go\server.pid"

if (Test-Path $pidFile) {
    $pid = Get-Content $pidFile
    Write-Host "Stopping Go server (PID: $pid)..."
    
    try {
        Stop-Process -Id $pid -Force -ErrorAction Stop
        Remove-Item $pidFile -Force
        Write-Host "✅ Server stopped successfully"
    } catch {
        Write-Host "⚠️  Process not found (already stopped?)"
        Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
    }
} else {
    Write-Host "No PID file found, trying to stop by process name..."
    $processes = Get-Process -Name "traffic-engine" -ErrorAction SilentlyContinue
    
    if ($processes) {
        $processes | Stop-Process -Force
        Write-Host "✅ Stopped $($processes.Count) traffic-engine process(es)"
    } else {
        Write-Host "⚠️  No traffic-engine processes running"
    }
}

# Wait a moment for port to be released
Start-Sleep -Milliseconds 500
Write-Host "Port 8080 should be free now"
