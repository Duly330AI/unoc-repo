# Start Go Traffic Engine in background (Windows)
# This script starts the server detached from the current process

$processInfo = New-Object System.Diagnostics.ProcessStartInfo
$processInfo.FileName = "C:\noc_project\UNOC\unoc\engine-go\bin\traffic-engine.exe"
$processInfo.WorkingDirectory = "C:\noc_project\UNOC\unoc\engine-go"
$processInfo.UseShellExecute = $false
$processInfo.CreateNoWindow = $false
$processInfo.RedirectStandardOutput = $false
$processInfo.RedirectStandardError = $false

$process = New-Object System.Diagnostics.Process
$process.StartInfo = $processInfo
$process.Start() | Out-Null

Write-Host "✅ Go server started in background (PID: $($process.Id))"
Write-Host "   Listening on: http://localhost:8080"
Write-Host ""
Write-Host "To stop: Stop-Process -Id $($process.Id) -Force"
Write-Host "Or use: Get-Process -Name 'traffic-engine' | Stop-Process -Force"

# Save PID to file for easy cleanup
$process.Id | Out-File -FilePath "C:\noc_project\UNOC\unoc\engine-go\server.pid" -Encoding ASCII
Write-Host ""
Write-Host "PID saved to: engine-go\server.pid"
