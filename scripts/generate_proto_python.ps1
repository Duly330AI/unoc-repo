#!/usr/bin/env pwsh
# Generate Python gRPC code from proto files

Write-Host "🔧 Generating Python gRPC code from proto files..." -ForegroundColor Cyan

# Check if grpc_tools is installed
try {
    python -c "import grpc_tools" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ grpc_tools not installed!" -ForegroundColor Red
        Write-Host "Installing grpc_tools..." -ForegroundColor Yellow
        pip install grpcio grpcio-tools
        if ($LASTEXITCODE -ne 0) {
            Write-Host "❌ Failed to install grpc_tools!" -ForegroundColor Red
            exit 1
        }
    }
} catch {
    Write-Host "❌ Python not found!" -ForegroundColor Red
    exit 1
}

# Create output directory
$outputDir = "../backend/proto/port_summary"
if (-not (Test-Path $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
}

# Generate Python code
Write-Host "📦 Running protoc..." -ForegroundColor Yellow

Push-Location engine-go

python -m grpc_tools.protoc `
    --python_out=../backend/proto `
    --grpc_python_out=../backend/proto `
    --proto_path=proto `
    proto/port_summary/port_summary.proto

Pop-Location

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Proto generation failed!" -ForegroundColor Red
    exit 1
}

# Verify output files
$pb2File = "backend/proto/port_summary/port_summary_pb2.py"
$grpcFile = "backend/proto/port_summary/port_summary_pb2_grpc.py"

if ((Test-Path $pb2File) -and (Test-Path $grpcFile)) {
    Write-Host "✅ Proto files generated successfully!" -ForegroundColor Green
    Write-Host "   - $pb2File" -ForegroundColor Gray
    Write-Host "   - $grpcFile" -ForegroundColor Gray
    
    # Test import
    Write-Host "`n🧪 Testing import..." -ForegroundColor Yellow
    python -c "from backend.proto.port_summary import port_summary_pb2; print('✅ Import successful!')"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "`n🎉 All done! Python gRPC client is ready to use." -ForegroundColor Green
    } else {
        Write-Host "`n⚠️  Files generated but import test failed. Check PYTHONPATH." -ForegroundColor Yellow
    }
} else {
    Write-Host "❌ Output files not found!" -ForegroundColor Red
    exit 1
}
