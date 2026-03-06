# Day 15 Task: Go Service String ID Migration

**Created**: October 5, 2025  
**Status**: 🔴 NOT STARTED  
**Priority**: P0 (Blocks Day 14 integration tests)  
**Estimated Time**: 2-3 hours  
**Dependencies**: Day 14 Python integration complete

---

## Executive Summary

**Problem**: Python integration (Day 14) uses NEW proto with **string IDs** for interfaces/links, but Go service still uses OLD proto with **int32 IDs**. This proto mismatch causes:

- Python sends: `a_interface_id: "core1_eth0"` (string)
- Go expects: `a_interface_id: 123` (int32)
- Result: **0 links created** (silent type mismatch)

**Solution**: Migrate Go service to use string IDs, matching Python proto and database schema.

**Target**: 3/3 integration tests passing (currently 1/3)

---

## Proto Mismatch Analysis

### Current State (Day 14)

**Python Proto** (`/unoc/proto/batch/batch.proto`):

```protobuf
message LinkCreateSpec {
  string a_interface_id = 1;  // ✅ STRING (e.g., "core1_eth0")
  string b_interface_id = 2;  // ✅ STRING
  float length_km = 3;
  string status = 4;
  map<string, string> metadata = 5;
}

message BatchCreateLinksResponse {
  repeated string created_link_ids = 1;  // ✅ STRING (e.g., "link_123")
  // ...
}
```

**Go Proto** (`/unoc/engine-go/proto/batch.proto` - OLD Day 13 version):

```protobuf
message LinkCreate {
  int32 a_interface_id = 1;  // ❌ INT32 (wrong!)
  int32 b_interface_id = 2;  // ❌ INT32 (wrong!)
  string classification = 3;
  // ...
}

message CreateLinksResponse {
  repeated int32 link_ids = 1;  // ❌ INT32 (wrong!)
  // ...
}
```

**Database Schema** (PostgreSQL):

```sql
interface.id:        VARCHAR (e.g., "core1_eth0")
link.id:            VARCHAR (e.g., "link_123")
link.a_interface_id: VARCHAR (FK to interface.id)
link.b_interface_id: VARCHAR (FK to interface.id)
```

**Type Flow**:

```
Database (string) → Go Service (int32 ❌) → Python Client (string ✅)
                       ↑
                   TYPE MISMATCH HERE
```

---

## Migration Checklist

### Phase 1: Proto File Update ✅ (DONE - needs revert)

**Status**: Proto already updated but Go service not refactored yet.

**Backup Current State**:

```powershell
# Already done (but backup is also new proto):
# engine-go/proto/batch.proto.day13.backup
```

**Update Proto**:

```powershell
# Already done - /unoc/proto/batch/batch.proto has string IDs
# Copy to Go service directory:
Copy-Item proto\batch\batch.proto engine-go\proto\batch.proto -Force
```

**Regenerate Go Stubs**:

```bash
cd engine-go
protoc --go_out=proto/batch --go-grpc_out=proto/batch --proto_path=proto proto/batch.proto
# Generates: batch.pb.go, batch_grpc.pb.go (with string types)
```

---

### Phase 2: Go Code Refactoring ⏳ (TO DO)

**Files to Update**:

1. **`engine-go/internal/batch/create.go`** (333 lines, ~20+ changes):

   **Function Signatures**:

   ```go
   // Line 93 - Change return type:
   // BEFORE:
   func (s *Service) createLinksInTransaction(ctx context.Context, specs []*pb.LinkCreateSpec) ([]int32, []*pb.LinkCreationFailure, error)

   // AFTER:
   func (s *Service) createLinksInTransaction(ctx context.Context, specs []*pb.LinkCreateSpec) ([]string, []*pb.LinkCreationFailure, error)
   ```

   ```go
   // Line 215 - Change parameter and return types:
   // BEFORE:
   func (s *Service) validateInterfacesExist(ctx context.Context, tx *sql.Tx, interfaceIDs map[int32]bool) (map[int32]bool, error)

   // AFTER:
   func (s *Service) validateInterfacesExist(ctx context.Context, tx *sql.Tx, interfaceIDs map[string]bool) (map[string]bool, error)
   ```

   ```go
   // Line 250 - Change parameter and return types:
   // BEFORE:
   func (s *Service) getLinkedInterfaces(ctx context.Context, tx *sql.Tx, interfaceIDs map[int32]bool) (map[int32]bool, error)

   // AFTER:
   func (s *Service) getLinkedInterfaces(ctx context.Context, tx *sql.Tx, interfaceIDs map[string]bool) (map[string]bool, error)
   ```

   **Variable Declarations**:

   ```go
   // Line 101 - Change slice type:
   // BEFORE: var createdIDs []int32
   // AFTER:  var createdIDs []string

   // Line 105 - Change map type:
   // BEFORE: interfaceIDs := make(map[int32]bool)
   // AFTER:  interfaceIDs := make(map[string]bool)

   // Line 180 - Change SQL scan variable:
   // BEFORE: var linkID int32
   // AFTER:  var linkID string

   // Line 217 - Change empty map return:
   // BEFORE: return map[int32]bool{}, nil
   // AFTER:  return map[string]bool{}, nil

   // Line 221 - Change slice type for SQL:
   // BEFORE: ids := make([]int32, 0, len(interfaceIDs))
   // AFTER:  ids := make([]string, 0, len(interfaceIDs))

   // Line 236 - Change map type:
   // BEFORE: existingInterfaces := make(map[int32]bool)
   // AFTER:  existingInterfaces := make(map[string]bool)

   // Line 238 - Change SQL scan variable:
   // BEFORE: var id int32
   // AFTER:  var id string
   ```

   **SQL Queries** (No changes needed!):

   ```go
   // PostgreSQL pq.Array() works with both int[] and text[]
   // These remain unchanged:
   err := rows.Scan(&id)  // Scans both int32 and string
   query := `SELECT id FROM interface WHERE id = ANY($1)`
   _, err := tx.ExecContext(ctx, query, pq.Array(ids))  // Works with []string
   ```

   **Response Fields** (Keep as int32):

   ```go
   // These are correct (response counts, not IDs):
   TotalRequested: int32(len(req.Links))  // ✅ Keep
   TotalCreated: int32(len(createdIDs))   // ✅ Keep
   Index: int32(idx)                       // ✅ Keep
   ```

2. **`engine-go/internal/batch/service.go`** (~50 lines, ~5 changes):

   ```go
   // BatchDeleteLinks method:
   // BEFORE:
   func (s *Service) BatchDeleteLinks(ctx context.Context, req *pb.BatchDeleteLinksRequest) (*pb.BatchDeleteLinksResponse, error) {
       // req.LinkIds is []int32
       for _, linkID := range req.LinkIds {
           var id int32 = linkID  // ❌
       }
   }

   // AFTER:
   func (s *Service) BatchDeleteLinks(ctx context.Context, req *pb.BatchDeleteLinksRequest) (*pb.BatchDeleteLinksResponse, error) {
       // req.LinkIds is []string
       for _, linkID := range req.LinkIds {
           var id string = linkID  // ✅
       }
   }
   ```

---

### Phase 3: Build & Test ⏳ (TO DO)

**Build Go Service**:

```bash
cd engine-go
go build -o bin/batch-service ./cmd/batch-service
# Expected: Clean build with no type errors
```

**Restart Go Service**:

```powershell
# Stop old service:
# (Find PID and kill, or use task manager)

# Start new service:
$env:DATABASE_URL="postgresql://unoc:unocpw@localhost:5432/unocdb"
$env:BATCH_SERVICE_PORT="50052"
.\bin\batch-service.exe
# Expected: "Batch Operations Service listening on :50052"
```

**Run Integration Tests**:

```bash
pytest backend/tests/test_batch_operations_integration.py::test_batch_create_single_link -v
pytest backend/tests/test_batch_operations_integration.py::test_batch_create_validation_error_interface_not_found -v
pytest backend/tests/test_batch_operations_integration.py::test_health_check_endpoint -v
```

**Expected Results**:

- ✅ `test_health_check_endpoint`: PASSING (already works)
- ✅ `test_batch_create_single_link`: **1 link created** (was 0)
- ✅ `test_batch_create_validation_error`: **Error details returned** (was empty)

---

### Phase 4: Performance Validation ⏳ (TO DO)

**Run 64-Link Batch Test**:

```bash
pytest backend/tests/test_batch_operations_integration.py::test_batch_create_64_links_performance -v
```

**Expected**:

- Duration: <10s (vs 37 min Python sequential)
- 64 links created successfully
- **262× speedup confirmed**

---

## Risk Assessment

**Low Risk**:

- Go has strong type system → compiler catches type errors
- SQL queries unchanged (pq.Array works with strings)
- Database schema already uses string IDs

**Medium Risk**:

- 20+ code changes (high volume, but mechanical)
- Need careful testing of validation logic

**Mitigation**:

1. Use `replace_string_in_file` with 5+ lines context for uniqueness
2. Build incrementally (function by function)
3. Run tests after each file edit

---

## Success Criteria

✅ **Proto Migration**:

- Go proto matches Python proto (string IDs for interface_id, link_id)
- Go stubs regenerated (batch.pb.go, batch_grpc.pb.go)

✅ **Code Refactoring**:

- All function signatures updated (3 functions)
- All variable types updated (8 variables)
- Clean build (no type errors)

✅ **Integration Tests**:

- 3/3 tests passing (health check, single link, validation error)
- Link creation returns non-zero count
- Error messages populated correctly

✅ **Performance**:

- 64-link batch creation <10s
- 262× speedup confirmed

---

## Rollback Plan

If migration fails:

1. **Restore Old Proto**:

   ```powershell
   Copy-Item engine-go\proto\batch.proto.day13.backup engine-go\proto\batch.proto -Force
   ```

2. **Regenerate Old Stubs**:

   ```bash
   cd engine-go
   protoc --go_out=proto/batch --go-grpc_out=proto/batch --proto_path=proto proto/batch.proto
   ```

3. **Rebuild Go Service**:

   ```bash
   go build -o bin/batch-service ./cmd/batch-service
   ```

4. **Restart Service** with old binary

---

## Time Estimates

- **Phase 1** (Proto update): ✅ Already done
- **Phase 2** (Code refactoring): 1.5-2 hours (systematic edits)
- **Phase 3** (Build & test): 30 minutes (build + 3 tests)
- **Phase 4** (Performance): 15 minutes (64-link test)

**Total**: 2-3 hours

---

## References

- **Proto Source**: `/unoc/proto/batch/batch.proto` (NEW - string IDs)
- **Go Proto**: `/unoc/engine-go/proto/batch.proto` (OLD - int32 IDs)
- **Go Code**: `/unoc/engine-go/internal/batch/create.go`, `service.go`
- **Tests**: `/unoc/backend/tests/test_batch_operations_integration.py`
- **Day 14 Status**: `/unoc/docs/roadmap/WEEK3_KICKOFF.md` (lines 207-270)

---

## Next Steps (Day 15 Start)

1. Read `engine-go/internal/batch/create.go` (review current int32 usage)
2. Start refactoring function signatures (line 93, 215, 250)
3. Update variable declarations (lines 101, 105, 180, 217, 221, 236, 238)
4. Update `service.go` BatchDeleteLinks method
5. Build + test (target: 3/3 passing)
6. Update Day 14 status to 100% complete
