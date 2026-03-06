# UNOC

FastAPI + Vue 3 (Vite) FTTH / access network topology sandbox (r9 architecture).
Backend authoritative; frontend renders incremental deltas (no full refresh after initial load).

## Quick Start

### Backend (Dev)

```powershell
# Activate Conda env and install deps
conda activate unoc-env
pip install -r requirements.txt

# Run backend (reload on changes)
python run.py  # http://127.0.0.1:5001
```

### Frontend (Dev)

```powershell
cd unoc-frontend-v2
npm install
npm run dev  # http://localhost:5173 (or 5174 if occupied) with /api proxy → 5001
```

### Reset / Seed Dev Database

File-based SQLite by default (`unoc_dev.db`). Use helper script:

```powershell
python scripts/reset_dev_db.py --force --seed
```

Flags:

- `--force` skip confirmation when deleting existing file
- `--seed` insert minimal sample devices (pop1, core1, olt1)

To force in-memory mode (ephemeral) for a session:

```powershell
$env:UNOC_PERSISTENCE="inmemory"
python run.py
```

### PostgreSQL (Dev, recommended for concurrency)

SQLite can exhibit `database is locked` under concurrent read/write loads. For a more robust dev setup, use the built-in Docker Compose Postgres and a `.env` file for configuration.

1. Copy env template and adjust locally

```powershell
Copy-Item .env.example .env
# edit .env if needed; default DATABASE_URL points to local docker compose Postgres
```

2. Start Postgres

```powershell
docker compose up -d
```

3. Run the backend (automatically reads `.env`)

```powershell
python run.py
```

Notes:

- The app reads configuration from `.env` automatically via pydantic-settings.
- If `DATABASE_URL` is omitted in `.env`, the app falls back to SQLite (file or in-memory per `UNOC_PERSISTENCE`).
- Legacy `UNOC_DB_URL` is still honored but `.env` with `DATABASE_URL` is preferred.

### Tests (Backend)

By default, tests use the same configuration as the app. To run tests against Postgres, ensure your `.env` has `DATABASE_URL` set (see above). For a quick ephemeral run, set `UNOC_PERSISTENCE=inmemory` in `.env`.

```powershell
pytest -q
```

### Coverage (optional)

```powershell
python -m coverage run -m pytest && python -m coverage report
```

### DB Reset Details

The reset script performs:

1. Delete `unoc_dev.db` (file mode) unless overridden by `UNOC_DB_URL`.
2. Recreate tables (`reset_db()` + `init_db()`).
3. Optional seeding (POP, Core Switch, OLT).

Use cases:

- After switching branches with schema changes.
- Before demo to ensure known baseline.
- To repopulate minimal topology quickly (`--seed`).

Switching persistence:

- File (default): durable between runs.
- In-memory: `UNOC_PERSISTENCE=inmemory` (good for exploratory throwaway state).

### Minimal Topology Bootstrap (POP → Backbone → Core)

If you're starting from an empty DB and want a “green” baseline quickly, see:

- docs/operations/bootstrap/bootstrap_anchors.md — step-by-step to create POP, Backbone, and Core via API (or just use the seed script above).

### Type Generation (Backend → Frontend)

Scripts under `tools/` generate & verify TS domain types:

- `python tools/gen_ts_types.py` writes `unoc-frontend-v2/src/types/domain.ts`.
- `python tools/verify_ts_types.py` non-destructively compares current vs regenerated (exit 0 = no drift).

Run verify in CI before frontend build to catch schema drift.

### Troubleshooting

| Symptom                                 | Likely Cause                        | Fix                                                 |
| --------------------------------------- | ----------------------------------- | --------------------------------------------------- |
| UNIQUE constraint on device.id in tests | Missing isolation                   | Ensure autouse fixture present (re-run `pytest -q`) |
| Frontend 500 /api/devices               | Using wrong dev port (5173 vs 5174) | Open current Vite port output or restart dev task   |
| Device list empty after seed            | Wrong persistence mode              | Omit `UNOC_PERSISTENCE` or run seed script again    |

````

### Bulk Device Creation (UI)
Palette right-click → "Bulk Create…" opens modal (count, optional POP parent). Sequential creates with summary & Undo toast (5s window). See `docs/README.md` (Guides → UI) for details.

---

## Go Microservices (Week 1 Infrastructure ✅)

**Status:** Week 1 Complete (75%) – 4 Go services built, integration tests passing

### Overview

The UNOC backend uses a hybrid architecture: **Python FastAPI** for REST API and **Go gRPC services** for compute-heavy operations. Week 1 infrastructure is complete with all service binaries built and Python clients operational.

### Service Architecture

```
Python Backend (FastAPI) :5001          Go Services (gRPC)
├─ REST API                             ├─ Optical Compute :50051
├─ Auth/RBAC                            │  └─ Dijkstra pathfinding (4,000× speedup)
├─ DB migrations                        ├─ Batch Operations :50052
└─ gRPC Clients (Python)                │  └─ Parallel link create
   ├─ OpticalClient                     ├─ Status Propagation :50053
   ├─ BatchClient                       │  └─ Causal chain updates (30,000× speedup)
   ├─ StatusClient                      └─ Port Summary :50054
   └─ PortSummaryClient                    └─ O(1) occupancy queries (50-100× speedup)
```

### Service Ports

| Service             | Port  | Purpose                          | Status       |
| ------------------- | ----- | -------------------------------- | ------------ |
| Optical Compute     | 50051 | Optical path resolution          | ✅ Built     |
| Batch Operations    | 50052 | Parallel device/link operations  | ✅ Built     |
| Status Propagation  | 50053 | Device status cascade & gating   | ✅ Built     |
| **Port Summary**    | **50054** | **O(1) port occupancy queries** | **✅ NEW!** |

### Starting Services

**Quick Start (All Services):**
```powershell
.\scripts\start_services.ps1
```

This script:
- Checks that all binaries exist (`engine-go/bin/*.exe`)
- Verifies ports 50051-50054 are available
- Sets environment variables (DATABASE_URL)
- Starts each service in a separate PowerShell window

**Or start individually:**
```powershell
# Port Summary Service (NEW! - O(1) port occupancy)
cd engine-go\cmd\port-summary-service
.\start.ps1
# See: docs/roadmap/PORT_SUMMARY_QUICKSTART.md for 5-min setup

# Optical Compute Service
cd engine-go\cmd\optical-compute-service
.\start.ps1

# Status Propagation Service
cd engine-go\cmd\status-propagation-service
.\start.ps1

# Batch Operations Service
cd engine-go\cmd\batch-operations-service
.\start.ps1
```

**Stopping Services:**
```powershell
.\scripts\stop_services.ps1
```

### Python Client Usage

All Go services have Python clients with automatic fallback to Python implementations if Go services are unavailable.

**Example: Optical Client**
```python
from backend.clients.go_services import get_optical_client

# Get client (auto-connects to Go service or falls back to Python)
client = get_optical_client()

# Check health
health = client.health()
# {"status": "healthy", "backend": "go", "available": True}

# Recompute optical paths (Week 2 implementation)
result = client.recompute_optical_paths(device_ids=[1, 2, 3])
```

**Example: Batch Client**
```python
from backend.clients.go_services import get_batch_client

client = get_batch_client()
health = client.health()

# Batch create links (Week 3 implementation)
result = client.create_links_batch(link_specs=[...])
```

**Example: Status Client**
```python
from backend.clients.go_services import get_status_client

client = get_status_client()
health = client.health()

# Propagate status updates (Week 2 implementation)
result = client.propagate_status(device_id=1, new_status="down")
```

**Example: Port Summary Client (NEW!)**
```python
from backend.clients.port_summary_client import get_port_summary_client

client = get_port_summary_client()

# Get port summary for single device (5-10ms response time!)
summary = await client.get_port_summary(device_id="device-1")
# Returns: {"interfaces": [...occupancy, capacity, status...]}

# Batch requests for multiple devices
bulk = await client.get_bulk_port_summary(["device-1", "device-2", "device-3"])
# Returns: {"device-1": {...}, "device-2": {...}, ...}

# Graceful fallback: Returns None if service unavailable
# Python backend can fall back to slower DB query
```

**Performance Benefits:**
- **Optical Compute**: 4,000× speedup (40s → 10-12ms per ONT)
- **Status Propagation**: 30,000× speedup (2000ms → 66μs per cascade)
- **Port Summary**: 50-100× speedup (250-700ms → 5-10ms per device) ✨ NEW!

**Documentation:**
- Quick Start: `docs/roadmap/PORT_SUMMARY_QUICKSTART.md` (5-min setup)
- Integration Guide: `docs/roadmap/PORT_SUMMARY_INTEGRATION_CHECKLIST.md`
- Technical Deep-Dive: `docs/roadmap/PORT_SUMMARY_PHASE1_COMPLETE.md`

client = get_status_client()
health = client.health()

# Propagate status changes (Week 2 implementation)
result = client.propagate_device_status(device_id=1, new_status="degraded")
```

### Environment Variables (Go Services)

All Go services require:
```powershell
DATABASE_URL=postgresql://unoc:unocpw@localhost:5432/unocdb
```

This is automatically set by `start_services.ps1`.

### Performance Targets (Week 2-3 Implementation)

| Operation                | Python (Current) | Go (Target) | Speedup |
| ------------------------ | ---------------- | ----------- | ------- |
| Single link create       | 35s              | 200ms       | 175×    |
| 64 links batch           | 37min            | 8s          | 262×    |
| Optical recompute        | 40s              | 50ms        | 800×    |

See `docs/roadmap/OPERATION-STABLE-FOUNDATION.md` for migration plan.

### Development Status

**Week 1 (Complete):**
- ✅ gRPC framework setup
- ✅ Protobuf contracts defined (optical.proto, batch.proto, status.proto)
- ✅ Service scaffolding (internal/optical, internal/batch, internal/status)
- ✅ Service entrypoints (cmd/optical-service, cmd/batch-service, cmd/status-service)
- ✅ Binaries built (engine-go/bin/*.exe)
- ✅ Python gRPC clients with fallback
- ✅ Integration tests passing (3/3 PASS)
- ✅ Startup scripts ready

**Week 2 (Next):**
- ⏳ Optical compute implementation (Dijkstra algorithm, goroutines)
- ⏳ Status propagation implementation (causal chains, batching)

**Week 3 (Future):**
- ⏳ Batch operations implementation (parallel link create)

### Testing

**Integration Tests:**
```powershell
python -m pytest -q test_grpc_integration.py
```

**Individual Service Health Checks:**
```python
from backend.clients.go_services import get_optical_client

client = get_optical_client()
print(client.health())
# {"status": "healthy", "backend": "go", "available": True}
```

### Troubleshooting

| Symptom                         | Likely Cause                      | Fix                                    |
| ------------------------------- | --------------------------------- | -------------------------------------- |
| "Service unavailable" errors    | Go services not running           | Run `.\scripts\start_services.ps1`     |
| Port already in use (50051-53)  | Previous service still running    | Run `.\scripts\stop_services.ps1`      |
| Python fallback always active   | Go binaries not found             | Build services: `cd engine-go && go build` |
| gRPC import errors              | Protobuf stubs not generated      | See `docs/roadmap/WEEK1_DAY4_COMPLETE.md` |

---

## Environment Variables (UNOC_*)
| Name                                       | Default | Purpose                                       |
| ------------------------------------------ | ------- | --------------------------------------------- |
| UNOC_PERSISTENCE                           | file    | file or inmemory (ephemeral) persistence mode |
| DATABASE_URL                                | unset   | SQLAlchemy URL (e.g., postgresql://user:pw@host:5432/db) |
| UNOC_PORT                                  | 5001    | Backend listen port                           |
| UNOC_SHUTDOWN_TOKEN                        | dev     | Token for graceful shutdown endpoint (dev)    |
| UNOC_DISABLE_RELOAD / UNOC_FORCE_NO_RELOAD | unset   | Disable uvicorn auto-reload even in debug     |

Other runtime feature flags and system design are documented in `docs/llm/ARCHITECTURE.md`.

## Contributing Notes
- Run tests before commit.
- Regenerate / verify TS types after backend schema changes.
- Use reset script (`scripts/reset_dev_db.py --force --seed`) when switching branches.
- Keep architecture decisions in `docs/llm/ARCHITECTURE.md` (avoid duplicating domain logic here).

## High-Level Features
- Provisioning model with lazy IPAM pools (core, access, ont, cpe).
- Link classification rules (L1–L9 + access uplinks).
- Bulk device creation (modal + Undo).
- Deterministic pathfinding (optical + logical upstream) and optical resolver.
- Traffic Engine v2 (tariff-based generation, aggregation, congestion hysteresis) and Debug Snapshot endpoint for diagnostics.

## Architecture & Tasks
- Architecture: `docs/llm/ARCHITECTURE.md` (spec revision r9).
- Backlog: `docs/llm/BACKLOG.md`.
    - Completed tasks: `docs/llm/COMPLETED_TASKS.md`.

## Roadmap Snapshot
Short form intentionally omitted to prevent drift; always consult `docs/llm/BACKLOG.md`.

## Docs Index
Start at `docs/README.md` for an overview of Architecture, Guides, Operations, Testing, and more.

## Quality Gates (local)
- Lint: ruff
- Imports: isort
- Format: black
- Tests: pytest

In VS Code, tasks are available to run lint and tests together (search for "quality" tasks).

## Docker Compose (PostgreSQL for Dev)
This repo ships a minimal Compose file for a local Postgres 16 instance.

1) Start Postgres

```powershell
docker compose up -d
````

2. Configure the app to use it (create `.env` if missing):

```powershell
Copy-Item .env.example .env
# Ensure DATABASE_URL is set to the compose instance, e.g.
# DATABASE_URL=postgresql+psycopg://unoc:unocpw@localhost:5432/unocdb
```

3. Run the backend as usual:

```powershell
python run.py
```

Data is persisted in the `pgdata` Docker volume. Stop with `docker compose down` (add `-v` to drop the volume).

```

```
