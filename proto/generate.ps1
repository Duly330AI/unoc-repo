# Proto Generation Script (PowerShell)
# Single source of truth: /unoc/proto/ contains all .proto files
# Generated files: backend/proto/ (Python), engine-go/proto/ (Go)

param(
    [Parameter(Position=0)]
    [ValidateSet("all", "go", "python", "clean", "help")]
    [string]$Target = "help"
)

$PROTO_DIR = "."
$BACKEND_PROTO_DIR = "..\backend\proto"
$GO_PROTO_DIR = "..\engine-go\proto"

$BATCH_PROTO = "$PROTO_DIR\batch\batch.proto"
$OPTICAL_PROTO = "$PROTO_DIR\optical\optical.proto"
$STATUS_PROTO = "$PROTO_DIR\status\status.proto"

function Generate-Go-Batch {
    Write-Host "🔧 Generating Go stubs for batch.proto..." -ForegroundColor Cyan
    protoc --proto_path=$PROTO_DIR `
        --go_out=$GO_PROTO_DIR --go_opt=paths=source_relative `
        --go-grpc_out=$GO_PROTO_DIR --go-grpc_opt=paths=source_relative `
        $BATCH_PROTO
    if ($LASTEXITCODE -ne 0) { throw "Failed to generate Go stubs for batch.proto" }
}

function Generate-Go-Optical {
    Write-Host "🔧 Generating Go stubs for optical.proto..." -ForegroundColor Cyan
    protoc --proto_path=$PROTO_DIR `
        --go_out=$GO_PROTO_DIR --go_opt=paths=source_relative `
        --go-grpc_out=$GO_PROTO_DIR --go-grpc_opt=paths=source_relative `
        $OPTICAL_PROTO
    if ($LASTEXITCODE -ne 0) { throw "Failed to generate Go stubs for optical.proto" }
}

function Generate-Go-Status {
    Write-Host "🔧 Generating Go stubs for status.proto..." -ForegroundColor Cyan
    protoc --proto_path=$PROTO_DIR `
        --go_out=$GO_PROTO_DIR --go_opt=paths=source_relative `
        --go-grpc_out=$GO_PROTO_DIR --go-grpc_opt=paths=source_relative `
        $STATUS_PROTO
    if ($LASTEXITCODE -ne 0) { throw "Failed to generate Go stubs for status.proto" }
}

function Generate-Python-Batch {
    Write-Host "🔧 Generating Python stubs for batch.proto..." -ForegroundColor Cyan
    protoc --proto_path=$PROTO_DIR `
        --python_out=$BACKEND_PROTO_DIR `
        --pyi_out=$BACKEND_PROTO_DIR `
        --grpc_python_out=$BACKEND_PROTO_DIR `
        $BATCH_PROTO
    if ($LASTEXITCODE -ne 0) { throw "Failed to generate Python stubs for batch.proto" }
}

function Generate-Python-Optical {
    Write-Host "🔧 Generating Python stubs for optical.proto..." -ForegroundColor Cyan
    protoc --proto_path=$PROTO_DIR `
        --python_out=$BACKEND_PROTO_DIR `
        --pyi_out=$BACKEND_PROTO_DIR `
        --grpc_python_out=$BACKEND_PROTO_DIR `
        $OPTICAL_PROTO
    if ($LASTEXITCODE -ne 0) { throw "Failed to generate Python stubs for optical.proto" }
}

function Generate-Python-Status {
    Write-Host "🔧 Generating Python stubs for status.proto..." -ForegroundColor Cyan
    protoc --proto_path=$PROTO_DIR `
        --python_out=$BACKEND_PROTO_DIR `
        --pyi_out=$BACKEND_PROTO_DIR `
        --grpc_python_out=$BACKEND_PROTO_DIR `
        $STATUS_PROTO
    if ($LASTEXITCODE -ne 0) { throw "Failed to generate Python stubs for status.proto" }
}

function Generate-Go {
    Write-Host "🚀 Generating all Go stubs..." -ForegroundColor Green
    Generate-Go-Batch
    Generate-Go-Optical
    Generate-Go-Status
    Write-Host "✅ Go stubs generated in $GO_PROTO_DIR" -ForegroundColor Green
}

function Generate-Python {
    Write-Host "🚀 Generating all Python stubs..." -ForegroundColor Green
    Generate-Python-Batch
    Generate-Python-Optical
    Generate-Python-Status
    Write-Host "✅ Python stubs generated in $BACKEND_PROTO_DIR" -ForegroundColor Green
}

function Generate-All {
    Write-Host "🚀 Generating all proto stubs (Go + Python)..." -ForegroundColor Green
    Generate-Go
    Generate-Python
    Write-Host "✅ All proto stubs generated successfully" -ForegroundColor Green
}

function Clean-Generated {
    Write-Host "🧹 Cleaning generated files..." -ForegroundColor Yellow
    
    # Go files
    Remove-Item -Path "$GO_PROTO_DIR\batch\*.pb.go" -ErrorAction SilentlyContinue
    Remove-Item -Path "$GO_PROTO_DIR\optical\*.pb.go" -ErrorAction SilentlyContinue
    Remove-Item -Path "$GO_PROTO_DIR\status\*.pb.go" -ErrorAction SilentlyContinue
    Remove-Item -Path "$GO_PROTO_DIR\optical.pb.go", "$GO_PROTO_DIR\optical_grpc.pb.go" -ErrorAction SilentlyContinue
    Remove-Item -Path "$GO_PROTO_DIR\status.pb.go", "$GO_PROTO_DIR\status_grpc.pb.go" -ErrorAction SilentlyContinue
    
    # Python files
    Remove-Item -Path "$BACKEND_PROTO_DIR\batch\*_pb2.py", "$BACKEND_PROTO_DIR\batch\*_pb2.pyi", "$BACKEND_PROTO_DIR\batch\*_pb2_grpc.py" -ErrorAction SilentlyContinue
    Remove-Item -Path "$BACKEND_PROTO_DIR\optical\*_pb2.py", "$BACKEND_PROTO_DIR\optical\*_pb2.pyi", "$BACKEND_PROTO_DIR\optical\*_pb2_grpc.py" -ErrorAction SilentlyContinue
    Remove-Item -Path "$BACKEND_PROTO_DIR\status\*_pb2.py", "$BACKEND_PROTO_DIR\status\*_pb2.pyi", "$BACKEND_PROTO_DIR\status\*_pb2_grpc.py" -ErrorAction SilentlyContinue
    
    Write-Host "✅ Clean complete" -ForegroundColor Green
}

function Show-Help {
    Write-Host "Proto Generation Script (PowerShell)" -ForegroundColor Cyan
    Write-Host "=====================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Usage: .\generate.ps1 [target]" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Targets:" -ForegroundColor Green
    Write-Host "  all      - Generate all Go and Python stubs (default)"
    Write-Host "  go       - Generate Go stubs for all protos"
    Write-Host "  python   - Generate Python stubs for all protos"
    Write-Host "  clean    - Remove all generated stub files"
    Write-Host "  help     - Show this help message"
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor Yellow
    Write-Host "  .\generate.ps1 all       # Generate all stubs"
    Write-Host "  .\generate.ps1 go        # Generate only Go stubs"
    Write-Host "  .\generate.ps1 python    # Generate only Python stubs"
    Write-Host "  .\generate.ps1 clean     # Clean generated files"
    Write-Host ""
    Write-Host "Requirements:" -ForegroundColor Cyan
    Write-Host "  - protoc (Protocol Buffer compiler)"
    Write-Host "  - protoc-gen-go (Go plugin)"
    Write-Host "  - protoc-gen-go-grpc (Go gRPC plugin)"
    Write-Host "  - grpcio-tools (Python: pip install grpcio-tools)"
    Write-Host ""
    Write-Host "Workflow:" -ForegroundColor Green
    Write-Host "  1. Edit .proto files in proto/batch/, proto/optical/, proto/status/"
    Write-Host "  2. Run '.\generate.ps1 all' to regenerate stubs"
    Write-Host "  3. Commit both source .proto files and generated stubs"
}

# Main execution
try {
    switch ($Target) {
        "all"    { Generate-All }
        "go"     { Generate-Go }
        "python" { Generate-Python }
        "clean"  { Clean-Generated }
        "help"   { Show-Help }
    }
} catch {
    Write-Host "❌ Error: $_" -ForegroundColor Red
    exit 1
}
