# UNOC Docker Compose Setup

🐳 **Complete Docker Compose setup for UNOC with all Go services + Python backend + Monitoring**

## 🚀 Quick Start

### Prerequisites

- Docker Desktop 24+ installed and running
- 8GB RAM minimum (16GB recommended)
- 20GB disk space

### Start All Services

```powershell
# Build and start (first time)
.\docker-start.ps1 -Build

# Start (subsequent times)
.\docker-start.ps1

# Check status
.\docker-start.ps1 -Status

# View logs
.\docker-start.ps1 -Logs
.\docker-start.ps1 -Logs -Service batch-service

# Stop all
.\docker-start.ps1 -Stop
```

## 📊 Services & Ports

| Service             | Port  | URL                          | Credentials    |
| ------------------- | ----- | ---------------------------- | -------------- |
| **Backend**         | 5001  | http://localhost:5001/health | -              |
| **PostgreSQL**      | 5432  | localhost:5432               | unoc/unocpw    |
| **Traffic Engine**  | 8080  | http://localhost:8080/health | -              |
| **Status Service**  | 50053 | gRPC only                    | -              |
| **Optical Service** | 50051 | gRPC only                    | -              |
| **Batch Service**   | 50052 | gRPC only                    | -              |
| **Prometheus**      | 9090  | http://localhost:9090        | -              |
| **Grafana**         | 3000  | http://localhost:3000        | admin/unoc2025 |

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    Docker Network (172.28.0.0/16)            │
│                                                              │
│  ┌─────────────┐                                            │
│  │ PostgreSQL  │◄────────────────┐                          │
│  │   (5432)    │                 │                          │
│  └─────────────┘                 │                          │
│         ▲                        │                          │
│         │                        │                          │
│    ┌────┴─────────────────┬─────┴────┬──────────┐          │
│    │                      │          │          │          │
│ ┌──┴───────┐  ┌─────────┴┐  ┌──────┴─┐  ┌─────┴─────┐    │
│ │ Traffic  │  │  Status  │  │Optical │  │   Batch   │    │
│ │  (8080)  │  │ (50053)  │  │(50051) │  │  (50052)  │    │
│ └──────────┘  └──────────┘  └────┬───┘  └─────▲─────┘    │
│                                   │            │          │
│                                   └────────────┘          │
│                                   (gRPC dependency)        │
│                                                            │
│  ┌─────────────────────────────────────────────┐          │
│  │          Python Backend (5001)               │          │
│  │     (depends on all Go services)             │          │
│  └─────────────────────────────────────────────┘          │
│                                                            │
│  ┌──────────────┐         ┌──────────────┐               │
│  │ Prometheus   │────────►│   Grafana    │               │
│  │   (9090)     │         │    (3000)    │               │
│  └──────────────┘         └──────────────┘               │
└──────────────────────────────────────────────────────────────┘
```

## 🔍 Service Dependencies

**CRITICAL:** Services must start in this order:

1. **PostgreSQL** (5432) - Database layer
2. **Optical Service** (50051) - ⚠️ MUST START FIRST (Go service)
3. **Batch Service** (50052) - Depends on Optical (gRPC calls)
4. **Status Service** (50053) - Independent (Go service)
5. **Traffic Engine** (8080) - Independent (Go service)
6. **Backend** (5001) - Depends on all Go services

Docker Compose handles this automatically via `depends_on` and health checks.

## 📋 Common Commands

### Docker Compose

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# Restart specific service
docker-compose restart batch-service

# View logs
docker-compose logs -f
docker-compose logs -f batch-service
docker-compose logs --tail=100 optical-service

# Check status
docker-compose ps

# Rebuild and restart
docker-compose up -d --build

# Stop and remove everything (including volumes)
docker-compose down -v
```

### Health Checks

```bash
# Backend
curl http://localhost:5001/health

# Traffic Engine
curl http://localhost:8080/health

# Prometheus
curl http://localhost:9090/-/healthy

# Grafana
curl http://localhost:3000/api/health

# PostgreSQL
docker exec -it unoc-postgres psql -U unoc -d unocdb -c "SELECT 1;"
```

### Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f batch-service

# Last 100 lines
docker-compose logs --tail=100 optical-service

# Since timestamp
docker-compose logs --since "2024-10-06T10:00:00"
```

### Database

```bash
# Connect to PostgreSQL
docker exec -it unoc-postgres psql -U unoc -d unocdb

# Run query
docker exec -it unoc-postgres psql -U unoc -d unocdb -c "SELECT COUNT(*) FROM link;"

# Backup database
docker exec unoc-postgres pg_dump -U unoc unocdb > backup.sql

# Restore database
cat backup.sql | docker exec -i unoc-postgres psql -U unoc -d unocdb
```

## 🐛 Troubleshooting

### Services Won't Start

**Problem:** `batch-service` shows "Restarting"

**Diagnosis:**

```bash
docker-compose logs batch-service
```

**Common Causes:**

1. Optical service not ready
2. Database connection failed
3. Port already in use

**Solution:**

```bash
# Stop all
docker-compose down

# Check if ports are free
netstat -ano | findstr "5001 5432 8080 50051 50052 50053"

# Start in correct order
docker-compose up -d postgres
timeout /t 10
docker-compose up -d optical-service
timeout /t 5
docker-compose up -d batch-service
docker-compose up -d backend
```

### "Connection Refused" Errors

**Problem:** Backend can't connect to Go services

**Check:**

```bash
# Verify network
docker network inspect unoc_unoc-network

# Test connectivity
docker exec unoc-backend ping optical-service
docker exec unoc-backend ping batch-service
```

**Solution:**

```bash
# Recreate network
docker-compose down
docker-compose up -d
```

### High Memory Usage

**Check:**

```bash
docker stats
```

**Solution:**

```bash
# Restart specific service
docker-compose restart batch-service

# Or restart all
docker-compose restart
```

### Logs Show "No Space Left"

**Check:**

```bash
docker system df
```

**Solution:**

```bash
# Clean up old images/containers
docker system prune -a

# Remove old volumes (WARNING: deletes data!)
docker volume prune
```

## 🔧 Development Tips

### Hot Reload (Backend)

The backend mounts `./backend` as read-only volume. To enable hot reload:

1. Edit `docker-compose.yml`:

   ```yaml
   backend:
     volumes:
       - ./backend:/app/backend:rw # Change :ro to :rw
     command: ['python', 'run.py'] # Change from gunicorn to run.py
   ```

2. Restart backend:
   ```bash
   docker-compose restart backend
   ```

### Building Go Services Locally

```bash
cd engine-go

# Build all services
make build-all

# Build specific service
go build -o bin/batch-service ./cmd/batch-service

# Run locally (not in Docker)
./bin/batch-service --port=50052
```

### Testing Changes

```bash
# Rebuild specific service
docker-compose build batch-service

# Restart with new image
docker-compose up -d batch-service

# Verify
docker-compose logs -f batch-service
```

## 📊 Monitoring

### Prometheus

Access: http://localhost:9090

**Useful Queries:**

```promql
# Batch create latency (P95)
histogram_quantile(0.95, rate(batch_create_duration_seconds_bucket[5m]))

# Batch throughput (links/sec)
rate(batch_create_links_total[1m])

# Error rate
rate(batch_create_errors_total[5m])
```

### Grafana

Access: http://localhost:3000 (admin/unoc2025)

**Dashboards:**

- Service Overview: All services status, latency, errors
- Batch Operations: Detailed batch metrics, throughput, optical coordination

## 🎯 Performance Validation

Run the benchmark inside Docker:

```bash
# Execute benchmark in backend container
docker exec -it unoc-backend python scripts/benchmark_batch_detailed.py

# Expected result: ~11ms for 64 links (209,489× speedup)
```

## 📝 Files

```
.
├── docker-compose.yml           # Main compose file (8 services)
├── docker-start.ps1             # Quick start script
├── Dockerfile.backend           # Python FastAPI image
├── .dockerignore                # Exclude unnecessary files
├── engine-go/
│   ├── Dockerfile.traffic       # Traffic Engine image
│   ├── Dockerfile.status        # Status Service image
│   ├── Dockerfile.optical       # Optical Service image
│   └── Dockerfile.batch         # Batch Service image
├── logs/                        # Service logs (mounted volumes)
│   ├── backend/
│   ├── batch/
│   ├── optical/
│   ├── status/
│   ├── traffic/
│   └── postgres/
└── ops/                         # Monitoring configs
    ├── prometheus/
    │   ├── prometheus.yml       # Scrape configs
    │   └── alerts/              # Alert rules
    └── grafana/
        ├── provisioning/        # Auto-provisioning
        └── dashboards/          # Dashboard JSONs
```

## 🚀 Next Steps

After Docker Compose is working:

1. **Production Deployment** (systemd units)
   - See: `docs/roadmap/WEEK3_DAYS18-19_PRODUCTION.md`
2. **Monitoring Setup**
   - Configure Prometheus alerts
   - Create Grafana dashboards
3. **Documentation**
   - DEPLOYMENT.md
   - MONITORING.md
   - TROUBLESHOOTING.md

## 📚 Resources

- [Docker Compose Docs](https://docs.docker.com/compose/)
- [UNOC Architecture](docs/GO-SERVICES-OVERVIEW.md)
- [Performance Results](docs/roadmap/WEEK3_PERFORMANCE_RESULTS.md)
- [Production Deployment](docs/roadmap/WEEK3_DAYS18-19_PRODUCTION.md)

---

**Status:** ✅ Week 3 Optimization Complete (209,489× speedup validated)  
**Next:** Production deployment with systemd + monitoring (Days 18-19)
