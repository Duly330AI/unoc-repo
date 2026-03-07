# Protocol Buffer Generation Workflow

**Status**: ✅ Active (as of Day 15 - Week 3)  
**Owner**: Infrastructure Team  
**Last Updated**: 2025-10-05

## Overview

This document describes the Protocol Buffer (proto) generation workflow for the UNOC project. We use gRPC for communication between Python (FastAPI backend) and Go (high-performance services).

## Architecture Principle: Single Source of Truth

**All `.proto` source files live in `/unoc/proto/`**. Generated files are automatically created in language-specific directories:

```
/unoc/proto/                          ← SINGLE SOURCE OF TRUTH ✅
  ├── batch/batch.proto               (Batch operations service)
  ├── optical/optical.proto           (Optical path computation)
  ├── status/status.proto             (Status propagation)
  ├── Makefile                        (Linux/Mac generation)
  └── generate.ps1                    (Windows generation)

/unoc/backend/proto/                  ← GENERATED PYTHON STUBS
  ├── batch_pb2.py, batch_pb2_grpc.py
  ├── optical/optical_pb2.py, optical_pb2_grpc.py
  └── status/status_pb2.py, status_pb2_grpc.py

/unoc/engine-go/proto/                ← GENERATED GO STUBS
  ├── batch/batch.pb.go, batch_grpc.pb.go
  ├── optical.pb.go, optical_grpc.pb.go
  └── status.pb.go, status_grpc.pb.go
```

## Prerequisites

### Required Tools

1. **protoc** (Protocol Buffer Compiler)

   ```bash
   # Check installation
   protoc --version  # Should be >= 3.19.0

   # Install (Windows with Chocolatey)
   choco install protoc

   # Install (Linux)
   sudo apt install protobuf-compiler

   # Install (macOS)
   brew install protobuf
   ```

2. **Go Plugins**

   ```bash
   go install google.golang.org/protobuf/cmd/protoc-gen-go@latest
   go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest

   # Verify plugins are in PATH
   which protoc-gen-go
   which protoc-gen-go-grpc
   ```

3. **Python gRPC Tools**
   ```bash
   # In UNOC virtual environment
   conda activate unoc-env
   pip install grpcio-tools
   ```

## Generation Workflow

### Method 1: Automatic (Recommended)

**Windows (PowerShell)**:

```powershell
cd proto
.\generate.ps1 all       # Generate all stubs (Go + Python)
.\generate.ps1 go        # Generate only Go stubs
.\generate.ps1 python    # Generate only Python stubs
.\generate.ps1 clean     # Remove all generated files
.\generate.ps1 help      # Show usage
```

**Linux/Mac (Make)**:

```bash
cd proto
make all              # Generate all stubs (Go + Python)
make generate-go      # Generate only Go stubs
make generate-python  # Generate only Python stubs
make clean            # Remove all generated files
make help             # Show usage
```

### Method 2: Manual (For Debugging)

**Generate Go Stubs**:

```bash
cd proto
protoc --proto_path=. \
  --go_out=../engine-go/proto --go_opt=paths=source_relative \
  --go-grpc_out=../engine-go/proto --go-grpc_opt=paths=source_relative \
  batch/batch.proto
```

**Generate Python Stubs**:

```bash
cd proto
protoc --proto_path=. \
  --python_out=../backend/proto \
  --pyi_out=../backend/proto \
  --grpc_python_out=../backend/proto \
  batch/batch.proto
```

## Standard Workflow: Adding/Modifying Protos

### Step 1: Edit Proto File

```bash
# Edit the source .proto file
code proto/batch/batch.proto
```

### Step 2: Regenerate Stubs

```bash
cd proto
.\generate.ps1 all   # Windows
# OR
make all             # Linux/Mac
```

### Step 3: Verify Generated Files

```bash
# Check Python stubs
ls backend/proto/batch_pb2.py
ls backend/proto/batch_pb2_grpc.py

# Check Go stubs
ls engine-go/proto/batch/batch.pb.go
ls engine-go/proto/batch/batch_grpc.pb.go
```

### Step 4: Update Go Service Code

```go
// Example: Using generated types in Go
import pb "github.com/duly3/unoc-engine/proto/batch"

func (s *BatchService) BatchCreateLinks(
    ctx context.Context,
    req *pb.BatchCreateLinksRequest,
) (*pb.BatchCreateLinksResponse, error) {
    // Implementation using req.AInterfaceId (string)
    // ...
}
```

### Step 5: Update Python Client Code

```python
# Example: Using generated types in Python
from backend.proto import batch_pb2, batch_pb2_grpc

async def create_links_batch(interface_ids: list[str]):
    request = batch_pb2.BatchCreateLinksRequest(
        a_interface_id=interface_ids[0],
        b_interface_id=interface_ids[1],
    )
    response = await grpc_client.BatchCreateLinks(request)
    return response.created_link_ids
```

### Step 6: Rebuild Go Services

```bash
cd engine-go
go build -o bin/batch-service.exe ./cmd/batch-service
```

### Step 7: Run Integration Tests

```bash
# Run Python → Go gRPC integration tests
pytest backend/tests/test_batch_operations_integration.py -v
pytest backend/tests/test_optical_compute_integration.py -v
pytest backend/tests/test_status_propagation_integration.py -v
```

### Step 8: Commit All Changes

```bash
# Commit BOTH source .proto AND generated stubs
git add proto/batch/batch.proto
git add backend/proto/batch_pb2.py backend/proto/batch_pb2_grpc.py
git add engine-go/proto/batch/batch.pb.go engine-go/proto/batch/batch_grpc.pb.go
git commit -m "feat(proto): update batch service proto - add new field X"
```

## Common Proto Patterns

### 1. String IDs (Recommended)

```protobuf
message BatchCreateLinksRequest {
  string a_interface_id = 1;  // Use string UUIDs
  string b_interface_id = 2;
  string link_type = 3;
}
```

**Rationale**: PostgreSQL uses UUID (string), avoids int64 ↔ string conversions.

### 2. Repeated Fields for Bulk Operations

```protobuf
message BatchCreateLinksResponse {
  repeated string created_link_ids = 1;  // List of created link IDs
  int32 success_count = 2;
  int32 failure_count = 3;
}
```

### 3. Error Handling

```protobuf
message BatchCreateLinksResponse {
  repeated string created_link_ids = 1;
  repeated ValidationError errors = 2;  // Detailed error messages
}

message ValidationError {
  string field = 1;
  string message = 2;
  string error_code = 3;
}
```

### 4. Optional Fields (Proto3)

```protobuf
message LinkUpdateRequest {
  string link_id = 1;
  optional string new_status = 2;      // Use 'optional' for nullable fields
  optional double new_capacity_mbps = 3;
}
```

## Troubleshooting

### Issue: `protoc: command not found`

**Solution**: Install protoc (see Prerequisites section).

### Issue: `protoc-gen-go: program not found`

**Solution**:

```bash
go install google.golang.org/protobuf/cmd/protoc-gen-go@latest
# Ensure $GOPATH/bin is in PATH
export PATH="$PATH:$(go env GOPATH)/bin"
```

### Issue: Python imports fail (`ModuleNotFoundError: No module named 'batch_pb2'`)

**Solution**:

```bash
# Regenerate Python stubs
cd proto
.\generate.ps1 python

# Verify __init__.py exists
ls backend/proto/__init__.py
```

### Issue: Go build fails (`undefined: pb.BatchCreateLinksRequest`)

**Solution**:

```bash
# Regenerate Go stubs
cd proto
.\generate.ps1 go

# Verify go.mod has correct module path
cd engine-go
go mod tidy
```

### Issue: Generated files have import errors

**Solution**: Check `go_package` option in .proto file:

```protobuf
option go_package = "github.com/duly3/unoc-engine/proto/batch";
```

## Best Practices

### 1. ✅ DO: Version Proto Files

- Use semantic versioning in comments: `// v1.2.0`
- Document breaking changes in commit messages

### 2. ✅ DO: Commit Generated Files

- Generated stubs are part of the codebase
- Ensures consistency across environments
- Avoids "works on my machine" issues

### 3. ✅ DO: Use Descriptive Field Names

```protobuf
// ❌ BAD
string a = 1;
string b = 2;

// ✅ GOOD
string a_interface_id = 1;
string b_interface_id = 2;
```

### 4. ✅ DO: Document Fields

```protobuf
message BatchCreateLinksRequest {
  // UUID of the source interface (A-side)
  string a_interface_id = 1;

  // UUID of the destination interface (B-side)
  string b_interface_id = 2;

  // Link type: "fiber", "copper", "wireless" (optional, default: "fiber")
  optional string link_type = 3;
}
```

### 5. ❌ DON'T: Edit Generated Files Manually

- Changes will be overwritten on next generation
- Edit source .proto files instead

### 6. ❌ DON'T: Store Proto Source Files Outside `/unoc/proto/`

- Violates "single source of truth" principle
- Causes confusion about which version is canonical

## Migration History

### Day 15 (Week 3): Proto Cleanup & String ID Migration

- **Moved** all proto source files to `/unoc/proto/` (single source of truth)
- **Migrated** batch service from `int64` → `string` IDs
- **Created** `Makefile` and `generate.ps1` for automated generation
- **Deleted** duplicate proto files from `engine-go/proto/`
- **Result**: 3/3 integration tests passing ✅

### Day 13 (Week 3): Initial Go Service Proto Setup

- Created `proto/batch/batch.proto` with int64 IDs
- Generated initial Go/Python stubs
- Established gRPC communication between Python and Go

## Related Documentation

- [Week 3 Kickoff - Go Service Integration](../roadmap/WEEK3_KICKOFF.md)
- [Day 15 Completion Summary](../roadmap/DAY15_GO_SERVICE_STRING_IDS.md)
- [Architecture Overview](../architecture/ARCHITECTURE.md)
- [gRPC Best Practices](https://grpc.io/docs/guides/performance/)

## Contact

For questions about proto generation:

- **Slack**: `#unoc-backend-dev`
- **Owner**: Infrastructure Team
- **Escalation**: See `docs/CODEOWNERS`
