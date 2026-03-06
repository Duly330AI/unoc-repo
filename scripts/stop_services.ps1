# UNOC Go Services - Stop Script
# Week 1 Day 4: Stop all running Go microservices

Write-Host "=" -ForegroundColor Cyan -NoNewline
Write-Host ("=" * 60) -ForegroundColor Cyan
Write-Host " Stopping UNOC Go Services" -ForegroundColor Yellow
Write-Host "=" -ForegroundColor Cyan -NoNewline
Write-Host ("=" * 60) -ForegroundColor Cyan
Write-Host ""

$services = @("optical-service", "batch-service", "status-service")
$stopped = 0

foreach ($svc in $services) {
    $processes = Get-Process -Name $svc -ErrorAction SilentlyContinue
    if ($processes) {
        Write-Host "Stopping $svc..." -ForegroundColor Yellow
        $processes | Stop-Process -Force
        $stopped += $processes.Count
        Write-Host "  Stopped $($processes.Count) instance(s)" -ForegroundColor Green
    } else {
        Write-Host "$svc not running" -ForegroundColor Gray
    }
}

Write-Host ""
if ($stopped -gt 0) {
    Write-Host "Stopped $stopped service(s) successfully." -ForegroundColor Green
} else {
    Write-Host "No services were running." -ForegroundColor Gray
}
Write-Host ""
