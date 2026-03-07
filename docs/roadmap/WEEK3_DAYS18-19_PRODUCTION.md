# Week 3 - Days 18-19: Production Deployment

**Date:** 6-7 Oktober 2025  
**Duration:** 5-7 hours total  
**Status:** 🚀 READY TO START  
**Prerequisites:** ✅ Week 3 optimization complete (209,489× speedup validated)

---

## 🎯 **Mission: Production-Ready Deployment**

Transform the validated Go services into a production-ready deployment with:

- **Docker Compose** for local/dev environments
- **systemd units** for Linux production servers
- **Monitoring** with Prometheus + Grafana
- **Complete documentation** for operations

---

## 📋 **Phase 1: Deployment Setup (Day 18, ~3-4 hours)**

### **Task 1.1: Docker Compose (90 min)**

**Goal:** Single `docker-compose up` starts entire stack

**File:** `docker-compose.yml` (NEW)

**Services to Define:**

```yaml
version: '3.8'

services:
  # PostgreSQL Database
  postgres:
    image: postgres:16-alpine
    container_name: unoc-postgres
    environment:
      POSTGRES_DB: unocdb
      POSTGRES_USER: unoc
      POSTGRES_PASSWORD: unocpw
    ports:
      - '5432:5432'
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./logs/postgres:/var/log/postgresql
    healthcheck:
      test: ['CMD-SHELL', 'pg_isready -U unoc']
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  # Go Service: Traffic Engine (Port 8080)
  traffic-engine:
    build:
      context: ./engine-go
      dockerfile: Dockerfile.traffic
    container_name: unoc-traffic-engine
    ports:
      - '8080:8080'
    environment:
      - TRAFFIC_PORT=8080
      - LOG_LEVEL=info
    volumes:
      - ./logs/traffic:/var/log/traffic
    healthcheck:
      test: ['CMD', 'curl', '-f', 'http://localhost:8080/health']
      interval: 15s
      timeout: 5s
      retries: 3
    restart: unless-stopped
    depends_on:
      postgres:
        condition: service_healthy

  # Go Service: Status Propagation (Port 50053)
  status-service:
    build:
      context: ./engine-go
      dockerfile: Dockerfile.status
    container_name: unoc-status-service
    ports:
      - '50053:50053'
    environment:
      - STATUS_PORT=50053
      - LOG_LEVEL=info
      - DATABASE_URL=postgresql://unoc:unocpw@postgres:5432/unocdb
    volumes:
      - ./logs/status:/var/log/status
    healthcheck:
      test: ['CMD', '/app/status-service', '--health']
      interval: 15s
      timeout: 5s
      retries: 3
    restart: unless-stopped
    depends_on:
      postgres:
        condition: service_healthy

  # Go Service: Optical PathFinder (Port 50051) - MUST START BEFORE BATCH
  optical-service:
    build:
      context: ./engine-go
      dockerfile: Dockerfile.optical
    container_name: unoc-optical-service
    ports:
      - '50051:50051'
    environment:
      - OPTICAL_PORT=50051
      - LOG_LEVEL=info
      - DATABASE_URL=postgresql://unoc:unocpw@postgres:5432/unocdb
    volumes:
      - ./logs/optical:/var/log/optical
    healthcheck:
      test: ['CMD', '/app/optical-service', '--health']
      interval: 15s
      timeout: 5s
      retries: 3
    restart: unless-stopped
    depends_on:
      postgres:
        condition: service_healthy

  # Go Service: Batch Operations (Port 50052) - DEPENDS ON OPTICAL
  batch-service:
    build:
      context: ./engine-go
      dockerfile: Dockerfile.batch
    container_name: unoc-batch-service
    ports:
      - '50052:50052'
    environment:
      - BATCH_PORT=50052
      - OPTICAL_SERVICE_URL=optical-service:50051
      - LOG_LEVEL=info
      - DATABASE_URL=postgresql://unoc:unocpw@postgres:5432/unocdb
    volumes:
      - ./logs/batch:/var/log/batch
    healthcheck:
      test: ['CMD', '/app/batch-service', '--health']
      interval: 15s
      timeout: 5s
      retries: 3
    restart: unless-stopped
    depends_on:
      postgres:
        condition: service_healthy
      optical-service:
        condition: service_healthy

  # Python FastAPI Backend (Port 5001)
  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    container_name: unoc-backend
    ports:
      - '5001:5001'
    environment:
      - UNOC_ASYNC_MODE=threading
      - UNOC_PORT=5001
      - DATABASE_URL=postgresql+psycopg://unoc:unocpw@postgres:5432/unocdb
      - AUTO_ASSIGN_DEFAULT_HARDWARE=1
      - BATCH_SERVICE_URL=batch-service:50052
      - OPTICAL_SERVICE_URL=optical-service:50051
      - STATUS_SERVICE_URL=status-service:50053
      - TRAFFIC_ENGINE_URL=http://traffic-engine:8080
    volumes:
      - ./logs/backend:/var/log/backend
      - ./backend:/app/backend
    healthcheck:
      test: ['CMD', 'curl', '-f', 'http://localhost:5001/health']
      interval: 15s
      timeout: 5s
      retries: 3
    restart: unless-stopped
    depends_on:
      postgres:
        condition: service_healthy
      batch-service:
        condition: service_healthy
      optical-service:
        condition: service_healthy

  # Prometheus (Metrics Collection)
  prometheus:
    image: prom/prometheus:latest
    container_name: unoc-prometheus
    ports:
      - '9090:9090'
    volumes:
      - ./ops/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
    restart: unless-stopped

  # Grafana (Visualization)
  grafana:
    image: grafana/grafana:latest
    container_name: unoc-grafana
    ports:
      - '3000:3000'
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=unoc2025
      - GF_INSTALL_PLUGINS=grafana-piechart-panel
    volumes:
      - ./ops/grafana/provisioning:/etc/grafana/provisioning
      - ./ops/grafana/dashboards:/var/lib/grafana/dashboards
      - grafana_data:/var/lib/grafana
    restart: unless-stopped
    depends_on:
      - prometheus

volumes:
  postgres_data:
  prometheus_data:
  grafana_data:

networks:
  default:
    name: unoc-network
```

**Dockerfiles to Create:**

1. `engine-go/Dockerfile.traffic` - Traffic Engine
2. `engine-go/Dockerfile.status` - Status Service
3. `engine-go/Dockerfile.optical` - Optical Service
4. `engine-go/Dockerfile.batch` - Batch Service
5. `Dockerfile.backend` - Python FastAPI

**Testing:**

```bash
# Start entire stack
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f batch-service

# Verify health
curl http://localhost:5001/health
curl http://localhost:8080/health

# Stop all
docker-compose down
```

---

### **Task 1.2: systemd Units (60 min)**

**Goal:** Production Linux servers with auto-start on boot

**Files to Create:**

1. `ops/systemd/unoc-optical.service` - Optical Service (starts FIRST)
2. `ops/systemd/unoc-batch.service` - Batch Service (depends on optical)
3. `ops/systemd/unoc-status.service` - Status Service
4. `ops/systemd/unoc-traffic.service` - Traffic Engine
5. `ops/systemd/unoc-backend.service` - Python Backend

**Example: Optical Service (CRITICAL - must start first)**

**File:** `ops/systemd/unoc-optical.service`

```ini
[Unit]
Description=UNOC Optical PathFinder Service
Documentation=https://github.com/your-org/unoc
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=unoc
Group=unoc
WorkingDirectory=/opt/unoc/engine-go
ExecStart=/opt/unoc/engine-go/bin/optical-service
Restart=on-failure
RestartSec=5s
StandardOutput=journal
StandardError=journal
SyslogIdentifier=unoc-optical

# Environment
Environment="OPTICAL_PORT=50051"
Environment="LOG_LEVEL=info"
Environment="DATABASE_URL=postgresql://unoc:unocpw@localhost:5432/unocdb"

# Security (optional but recommended)
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/log/unoc

# Resource limits
LimitNOFILE=65536
TasksMax=4096

[Install]
WantedBy=multi-user.target
```

**Example: Batch Service (depends on Optical)**

**File:** `ops/systemd/unoc-batch.service`

```ini
[Unit]
Description=UNOC Batch Operations Service
Documentation=https://github.com/your-org/unoc
After=network.target postgresql.service unoc-optical.service
Requires=unoc-optical.service
Wants=postgresql.service

[Service]
Type=simple
User=unoc
Group=unoc
WorkingDirectory=/opt/unoc/engine-go
ExecStart=/opt/unoc/engine-go/bin/batch-service
Restart=on-failure
RestartSec=5s
StandardOutput=journal
StandardError=journal
SyslogIdentifier=unoc-batch

# Environment
Environment="BATCH_PORT=50052"
Environment="OPTICAL_SERVICE_URL=localhost:50051"
Environment="LOG_LEVEL=info"
Environment="DATABASE_URL=postgresql://unoc:unocpw@localhost:5432/unocdb"

# Wait for optical service to be ready
ExecStartPre=/bin/sleep 2

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/log/unoc

# Resource limits
LimitNOFILE=65536
TasksMax=4096

[Install]
WantedBy=multi-user.target
```

**Installation Script:**

**File:** `ops/systemd/install.sh`

```bash
#!/bin/bash
set -euo pipefail

echo "🚀 Installing UNOC systemd units..."

# Copy service files
sudo cp ops/systemd/*.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable services (auto-start on boot)
sudo systemctl enable unoc-optical.service
sudo systemctl enable unoc-batch.service
sudo systemctl enable unoc-status.service
sudo systemctl enable unoc-traffic.service
sudo systemctl enable unoc-backend.service

echo "✅ Services installed. Start with:"
echo "   sudo systemctl start unoc-optical"
echo "   sudo systemctl start unoc-batch"
echo "   sudo systemctl start unoc-backend"
echo ""
echo "Check status:"
echo "   sudo systemctl status unoc-optical"
echo "   journalctl -u unoc-optical -f"
```

**Testing:**

```bash
# Install
sudo bash ops/systemd/install.sh

# Start optical FIRST (critical dependency)
sudo systemctl start unoc-optical
sudo systemctl status unoc-optical

# Then start batch (depends on optical)
sudo systemctl start unoc-batch
sudo systemctl status unoc-batch

# Check logs
journalctl -u unoc-optical -f
journalctl -u unoc-batch -f

# Test auto-restart
sudo systemctl restart unoc-batch

# Test dependency (batch should fail if optical is down)
sudo systemctl stop unoc-optical
sudo systemctl status unoc-batch  # Should show failed/restarting
```

---

### **Task 1.3: Basic Monitoring Setup (60 min)**

**Goal:** Metrics collection + basic alerts

**File:** `ops/prometheus/prometheus.yml` (NEW)

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    cluster: 'unoc-production'
    replica: '1'

# Alertmanager configuration (optional, for production)
alerting:
  alertmanagers:
    - static_configs:
        - targets:
            - localhost:9093

# Load rules once and periodically evaluate them
rule_files:
  - 'alerts/*.yml'

scrape_configs:
  # Go Services (expose /metrics endpoint)
  - job_name: 'unoc-traffic-engine'
    static_configs:
      - targets: ['localhost:8080']
    metrics_path: /metrics
    scrape_interval: 5s

  - job_name: 'unoc-status-service'
    static_configs:
      - targets: ['localhost:50053']
    metrics_path: /metrics
    scrape_interval: 5s

  - job_name: 'unoc-optical-service'
    static_configs:
      - targets: ['localhost:50051']
    metrics_path: /metrics
    scrape_interval: 5s

  - job_name: 'unoc-batch-service'
    static_configs:
      - targets: ['localhost:50052']
    metrics_path: /metrics
    scrape_interval: 5s

  # Python Backend (FastAPI metrics)
  - job_name: 'unoc-backend'
    static_configs:
      - targets: ['localhost:5001']
    metrics_path: /metrics
    scrape_interval: 10s

  # PostgreSQL Exporter (optional)
  - job_name: 'postgres'
    static_configs:
      - targets: ['localhost:9187']
    scrape_interval: 15s

  # Prometheus self-monitoring
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
```

**Alert Rules:**

**File:** `ops/prometheus/alerts/services.yml` (NEW)

```yaml
groups:
  - name: unoc_services
    interval: 30s
    rules:
      # Service Down Alerts
      - alert: OpticalServiceDown
        expr: up{job="unoc-optical-service"} == 0
        for: 1m
        labels:
          severity: critical
          service: optical
        annotations:
          summary: 'Optical Service is down'
          description: 'Optical PathFinder service (port 50051) has been down for 1 minute. Batch operations will fail!'

      - alert: BatchServiceDown
        expr: up{job="unoc-batch-service"} == 0
        for: 1m
        labels:
          severity: critical
          service: batch
        annotations:
          summary: 'Batch Service is down'
          description: 'Batch Operations service (port 50052) has been down for 1 minute.'

      # Latency Alerts
      - alert: BatchCreateLatencyHigh
        expr: batch_create_duration_seconds{quantile="0.95"} > 0.1
        for: 5m
        labels:
          severity: warning
          service: batch
        annotations:
          summary: 'Batch create latency is high'
          description: '95th percentile batch create time is {{ $value }}s (threshold: 0.1s). Target: <0.1s.'

      - alert: OpticalRecomputeLatencyHigh
        expr: optical_recompute_duration_seconds{quantile="0.95"} > 0.05
        for: 5m
        labels:
          severity: warning
          service: optical
        annotations:
          summary: 'Optical recompute latency is high'
          description: '95th percentile optical recompute time is {{ $value }}s (threshold: 0.05s).'

      # Error Rate Alerts
      - alert: BatchCreateErrorRateHigh
        expr: rate(batch_create_errors_total[5m]) > 0.01
        for: 5m
        labels:
          severity: warning
          service: batch
        annotations:
          summary: 'Batch create error rate is high'
          description: 'Batch create errors: {{ $value }} errors/sec over 5min.'
```

**Testing:**

```bash
# Start Prometheus
docker-compose up -d prometheus

# Check targets
open http://localhost:9090/targets

# Query metrics
curl http://localhost:9090/api/v1/query?query=up

# Check alerts
open http://localhost:9090/alerts
```

---

## 📋 **Phase 2: Monitoring & Documentation (Day 19, ~2-3 hours)**

### **Task 2.1: Grafana Dashboards (60 min)**

**Goal:** Visual dashboards for operations

**Dashboard 1: Service Overview**

**File:** `ops/grafana/dashboards/service-overview.json` (NEW)

**Panels:**

1. **Service Status** (Single Stat)

   - Metric: `up{job=~"unoc-.*"}`
   - Display: Green (1) / Red (0)

2. **Request Rate** (Graph)

   - Metric: `rate(http_requests_total[5m])`
   - By service

3. **Latency (P50, P95, P99)** (Graph)

   - Metric: `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))`

4. **Error Rate** (Graph)
   - Metric: `rate(http_requests_total{status=~"5.."}[5m])`

**Dashboard 2: Batch Operations**

**File:** `ops/grafana/dashboards/batch-operations.json` (NEW)

**Panels:**

1. **Batch Create Duration** (Graph)

   - P50, P95, P99 latency
   - Target line at 100ms

2. **Batch Throughput** (Graph)

   - Links created per second
   - Total batches per minute

3. **Optical Coordination** (Graph)

   - Optical recompute calls
   - Affected ONTs per batch

4. **Error Breakdown** (Pie Chart)
   - By error type (validation, DB, optical, timeout)

**Provisioning:**

**File:** `ops/grafana/provisioning/dashboards/dashboards.yml`

```yaml
apiVersion: 1

providers:
  - name: 'UNOC Dashboards'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /var/lib/grafana/dashboards
```

**File:** `ops/grafana/provisioning/datasources/prometheus.yml`

```yaml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true
```

**Testing:**

```bash
# Start Grafana
docker-compose up -d grafana

# Login
open http://localhost:3000
# Username: admin
# Password: unoc2025

# Import dashboards
# Navigate to Dashboards → Browse → Import
# Upload ops/grafana/dashboards/*.json
```

---

### **Task 2.2: Documentation (90 min)**

**Goal:** Complete operational documentation

#### **2.2.1: DEPLOYMENT.md**

**File:** `docs/operations/DEPLOYMENT.md` (NEW)

````markdown
# UNOC Deployment Guide

## Prerequisites

- Docker 24+ (for Docker Compose)
- Linux with systemd (for production)
- PostgreSQL 16 (or use Docker Compose postgres service)
- Ports available: 5001, 5432, 8080, 50051-50053, 9090, 3000

## Docker Compose (Development/Local)

### Quick Start

1. **Clone repository:**
   ```bash
   git clone https://github.com/your-org/unoc.git
   cd unoc
   ```
````

2. **Start entire stack:**

   ```bash
   docker-compose up -d
   ```

3. **Verify services:**

   ```bash
   docker-compose ps
   curl http://localhost:5001/health
   ```

4. **View logs:**

   ```bash
   docker-compose logs -f batch-service
   ```

5. **Stop services:**
   ```bash
   docker-compose down
   ```

### Service Ports

| Service         | Port  | Protocol | Purpose            |
| --------------- | ----- | -------- | ------------------ |
| Backend         | 5001  | HTTP     | FastAPI REST API   |
| PostgreSQL      | 5432  | TCP      | Database           |
| Traffic Engine  | 8080  | HTTP     | Traffic simulation |
| Status Service  | 50053 | gRPC     | Status propagation |
| Optical Service | 50051 | gRPC     | PathFinder         |
| Batch Service   | 50052 | gRPC     | Batch operations   |
| Prometheus      | 9090  | HTTP     | Metrics            |
| Grafana         | 3000  | HTTP     | Dashboards         |

### Environment Variables

See `.env.example` for all configuration options.

## systemd (Production Linux)

### Installation

1. **Build Go services:**

   ```bash
   cd engine-go
   make build-all
   ```

2. **Install binaries:**

   ```bash
   sudo mkdir -p /opt/unoc/engine-go/bin
   sudo cp bin/* /opt/unoc/engine-go/bin/
   ```

3. **Install systemd units:**

   ```bash
   sudo bash ops/systemd/install.sh
   ```

4. **Start services (IN ORDER):**

   ```bash
   # 1. Start optical FIRST (critical dependency)
   sudo systemctl start unoc-optical

   # 2. Start batch (depends on optical)
   sudo systemctl start unoc-batch

   # 3. Start backend
   sudo systemctl start unoc-backend
   ```

### Service Management

```bash
# Check status
sudo systemctl status unoc-optical
sudo systemctl status unoc-batch

# View logs
journalctl -u unoc-optical -f
journalctl -u unoc-batch -f --since "10 minutes ago"

# Restart service
sudo systemctl restart unoc-batch

# Stop service
sudo systemctl stop unoc-batch

# Enable auto-start on boot
sudo systemctl enable unoc-optical
sudo systemctl enable unoc-batch
```

### Dependency Chain

**CRITICAL:** Services MUST start in this order:

```
1. PostgreSQL (5432)
   ↓
2. Optical Service (50051) ← MUST BE FIRST
   ↓
3. Batch Service (50052) ← Depends on Optical
   ↓
4. Backend (5001) ← Depends on Batch
```

**Why?** Batch service makes gRPC calls to Optical service. If Optical is not running, Batch will fail to start.

## Health Checks

### HTTP Services

```bash
# Backend
curl http://localhost:5001/health

# Traffic Engine
curl http://localhost:8080/health
```

### gRPC Services

```bash
# Batch Service
grpcurl -plaintext localhost:50052 health.Health/Check

# Optical Service
grpcurl -plaintext localhost:50051 health.Health/Check
```

### Database

```bash
psql -h localhost -U unoc -d unocdb -c "SELECT 1;"
```

## Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues and solutions.

````

#### **2.2.2: MONITORING.md**

**File:** `docs/operations/MONITORING.md` (NEW)

```markdown
# UNOC Monitoring Guide

## Metrics Overview

All Go services expose Prometheus metrics on `/metrics` endpoint.

### Key Metrics

#### Batch Operations

| Metric | Type | Description |
|--------|------|-------------|
| `batch_create_duration_seconds` | Histogram | Batch create latency (P50, P95, P99) |
| `batch_create_total` | Counter | Total batch create requests |
| `batch_create_errors_total` | Counter | Total batch create errors |
| `batch_create_links_total` | Counter | Total links created |

**Target:** P95 latency < 100ms

#### Optical PathFinder

| Metric | Type | Description |
|--------|------|-------------|
| `optical_recompute_duration_seconds` | Histogram | Recompute latency |
| `optical_recompute_total` | Counter | Total recompute requests |
| `optical_affected_onts` | Gauge | ONTs affected by last recompute |

**Target:** P95 latency < 50ms

### Prometheus Queries

**Batch create P95 latency:**
```promql
histogram_quantile(0.95,
  rate(batch_create_duration_seconds_bucket[5m])
)
````

**Batch throughput (links/sec):**

```promql
rate(batch_create_links_total[1m])
```

**Error rate:**

```promql
rate(batch_create_errors_total[5m])
```

## Grafana Dashboards

### Service Overview Dashboard

**URL:** http://localhost:3000/d/unoc-overview

**Panels:**

- Service status (up/down)
- Request rate (per service)
- Latency (P50, P95, P99)
- Error rate

### Batch Operations Dashboard

**URL:** http://localhost:3000/d/unoc-batch

**Panels:**

- Batch create duration (histogram)
- Throughput (links/sec)
- Optical coordination (calls, affected ONTs)
- Error breakdown (by type)

## Alerts

### Critical Alerts

| Alert              | Condition             | Action                                                          |
| ------------------ | --------------------- | --------------------------------------------------------------- |
| OpticalServiceDown | Service down for 1min | **CRITICAL** - Batch operations will fail! Restart immediately. |
| BatchServiceDown   | Service down for 1min | **CRITICAL** - No bulk operations possible. Check logs.         |

### Warning Alerts

| Alert                    | Condition            | Action                                       |
| ------------------------ | -------------------- | -------------------------------------------- |
| BatchCreateLatencyHigh   | P95 > 100ms for 5min | Check DB performance, optical service health |
| BatchCreateErrorRateHigh | Errors > 1% for 5min | Check logs for validation/DB errors          |

## Logging

### Log Locations

**Docker Compose:**

```bash
# View logs
docker-compose logs -f batch-service
docker-compose logs --tail=100 optical-service
```

**systemd:**

```bash
# View logs
journalctl -u unoc-batch -f
journalctl -u unoc-optical --since "1 hour ago"

# Follow multiple services
journalctl -u unoc-batch -u unoc-optical -f
```

### Log Levels

Set via environment variable `LOG_LEVEL`:

- `debug` - Verbose (dev only)
- `info` - Normal operations (default)
- `warn` - Warnings only
- `error` - Errors only

**Production:** Use `info` or `warn`

## Performance Baselines

### Expected Performance

| Metric                  | Expected | Threshold |
| ----------------------- | -------- | --------- |
| Batch create (64 links) | ~11ms    | <100ms    |
| Per link                | ~0.17ms  | <2ms      |
| Optical recompute       | <1ms     | <10ms     |

### Regression Detection

If P95 latency exceeds baselines by 2×:

1. Check database query plans
2. Check optical service health
3. Check PostgreSQL connection pool
4. Review recent code changes

````

#### **2.2.3: TROUBLESHOOTING.md**

**File:** `docs/operations/TROUBLESHOOTING.md` (NEW)

```markdown
# UNOC Troubleshooting Guide

## Common Issues

### 1. Batch Service Won't Start

**Symptom:**
````

Error: failed to connect to optical service: connection refused

````

**Cause:** Optical service not running or not reachable

**Solution:**
```bash
# 1. Check if optical service is running
sudo systemctl status unoc-optical

# 2. If not running, start it FIRST
sudo systemctl start unoc-optical

# 3. Wait 5 seconds for optical to be ready
sleep 5

# 4. Then start batch
sudo systemctl start unoc-batch
````

**Prevention:** Optical MUST start before Batch (systemd dependency handles this)

---

### 2. "'active' enum error" in Tests

**Symptom:**

```
LookupError: 'active' is not among the defined enum values
```

**Cause:** Schema mismatch - old test data uses `"active"`, DB expects `"UP"`

**Solution:**

```bash
# Fix test data
sed -i 's/"status": "active"/"status": "UP"/g' backend/tests/test_*.py

# Or use correct Status enum
from backend.models import Status
status = Status.UP  # Not "active"
```

---

### 3. Batch Create Latency > 100ms

**Symptom:** Grafana shows P95 > 100ms

**Possible Causes:**

1. Database slow queries
2. Optical service slow
3. Network latency
4. Connection pool exhausted

**Diagnosis:**

```bash
# 1. Check optical service latency
journalctl -u unoc-optical --since "5 minutes ago" | grep "duration_ms"

# 2. Check PostgreSQL query performance
psql -U unoc -d unocdb -c "SELECT * FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"

# 3. Check connection pool
curl http://localhost:50052/debug/pool
```

**Solutions:**

- If DB slow: Optimize queries, add indexes
- If optical slow: Check optical service logs
- If network: Check `OPTICAL_SERVICE_URL` in batch config
- If pool exhausted: Increase `MAX_CONNECTIONS` in config

---

### 4. Docker Compose Services Crash Loop

**Symptom:**

```bash
$ docker-compose ps
batch-service   Restarting (1)
```

**Diagnosis:**

```bash
# View recent logs
docker-compose logs --tail=50 batch-service

# Check health
docker inspect unoc-batch-service | grep -A 10 Health
```

**Common Causes:**

- Optical service not ready (wait longer)
- Database connection failed (check `DATABASE_URL`)
- Port already in use (check `netstat -tulpn | grep 50052`)

**Solution:**

```bash
# Stop all
docker-compose down

# Check ports
netstat -tulpn | grep -E "5001|5432|8080|5005[1-3]"

# Restart in correct order
docker-compose up -d postgres
sleep 10
docker-compose up -d optical-service
sleep 5
docker-compose up -d batch-service
docker-compose up -d backend
```

---

### 5. Grafana Dashboard Shows "No Data"

**Symptom:** Grafana panels show "No data"

**Diagnosis:**

```bash
# 1. Check if Prometheus is scraping
curl http://localhost:9090/api/v1/targets

# 2. Query metric directly
curl 'http://localhost:9090/api/v1/query?query=up{job="unoc-batch-service"}'
```

**Solution:**

1. Check service exposes `/metrics`:
   ```bash
   curl http://localhost:50052/metrics
   ```
2. Check Prometheus config (`ops/prometheus/prometheus.yml`)
3. Restart Prometheus:
   ```bash
   docker-compose restart prometheus
   ```

---

## Recovery Procedures

### Full System Restart

**Docker Compose:**

```bash
docker-compose down
docker-compose up -d
```

**systemd:**

```bash
# Stop all (reverse order)
sudo systemctl stop unoc-backend
sudo systemctl stop unoc-batch
sudo systemctl stop unoc-optical

# Start all (correct order)
sudo systemctl start unoc-optical
sleep 5
sudo systemctl start unoc-batch
sleep 5
sudo systemctl start unoc-backend
```

### Database Corruption

```bash
# 1. Stop all services
docker-compose down

# 2. Backup database
pg_dump -U unoc unocdb > backup_$(date +%Y%m%d).sql

# 3. Reset database
psql -U unoc -d postgres -c "DROP DATABASE unocdb;"
psql -U unoc -d postgres -c "CREATE DATABASE unocdb;"

# 4. Restore (if backup available)
psql -U unoc -d unocdb < backup_20251006.sql

# 5. Or run migrations
python -m alembic upgrade head

# 6. Restart services
docker-compose up -d
```

### Service Unresponsive

```bash
# 1. Check if process is alive
ps aux | grep batch-service

# 2. Check if port is listening
netstat -tulpn | grep 50052

# 3. Check resource usage
top -p $(pgrep batch-service)

# 4. If high CPU/memory, restart
sudo systemctl restart unoc-batch

# 5. If still unresponsive, check logs
journalctl -u unoc-batch --since "10 minutes ago"
```

---

## Getting Help

### Log Collection

When reporting issues, collect:

```bash
# Service logs (last 100 lines)
journalctl -u unoc-batch --lines=100 > batch.log
journalctl -u unoc-optical --lines=100 > optical.log

# System info
uname -a > sysinfo.txt
docker-compose version >> sysinfo.txt

# Service status
systemctl status unoc-* > services.txt
```

### Contact

- GitHub Issues: https://github.com/your-org/unoc/issues
- Slack: #unoc-support
- On-call: ops@your-org.com

```

---

## 🎯 **Deliverables Checklist**

### Day 18:
- [ ] `docker-compose.yml` - Complete stack definition
- [ ] `engine-go/Dockerfile.*` - 4 Dockerfiles for Go services
- [ ] `Dockerfile.backend` - Python FastAPI Dockerfile
- [ ] `ops/systemd/*.service` - 5 systemd unit files
- [ ] `ops/systemd/install.sh` - Installation script
- [ ] `ops/prometheus/prometheus.yml` - Prometheus config
- [ ] `ops/prometheus/alerts/services.yml` - Alert rules
- [ ] ✅ Test: `docker-compose up -d` works
- [ ] ✅ Test: systemd services start in correct order

### Day 19:
- [ ] `ops/grafana/dashboards/*.json` - 2 Grafana dashboards
- [ ] `ops/grafana/provisioning/*.yml` - Auto-provisioning configs
- [ ] `docs/operations/DEPLOYMENT.md` - Complete deployment guide
- [ ] `docs/operations/MONITORING.md` - Metrics & dashboards guide
- [ ] `docs/operations/TROUBLESHOOTING.md` - Common issues & recovery
- [ ] ✅ Test: Grafana dashboards show live metrics
- [ ] ✅ Test: Alerts trigger correctly (stop optical service)

---

## 📊 **Success Criteria**

### Functional:
- [ ] `docker-compose up -d` starts all 8 services
- [ ] Health checks pass for all services
- [ ] Batch create works end-to-end (benchmark script)
- [ ] Services restart automatically on crash
- [ ] Optical→Batch dependency chain enforced

### Performance:
- [ ] Batch create P95 < 100ms (current: ~11ms ✅)
- [ ] No service downtime during normal restarts
- [ ] Metrics scraped every 5-15s
- [ ] Grafana dashboards update in real-time

### Documentation:
- [ ] Deployment guide tested by fresh reader
- [ ] All commands in docs work as written
- [ ] Troubleshooting guide covers observed issues
- [ ] Service dependencies clearly documented

---

## 🚀 **Estimated Timeline**

| Phase | Duration | Status |
|-------|----------|--------|
| Docker Compose | 90 min | 🔜 Day 18 |
| systemd Units | 60 min | 🔜 Day 18 |
| Basic Monitoring | 60 min | 🔜 Day 18 |
| Grafana Dashboards | 60 min | 🔜 Day 19 |
| Documentation | 90 min | 🔜 Day 19 |
| **TOTAL** | **5-6 hours** | **Days 18-19** |

---

## 🎉 **Completion: Production-Ready Week 3!**

After Days 18-19, you will have:
- ✅ Docker Compose for dev environments
- ✅ systemd units for production servers
- ✅ Prometheus + Grafana monitoring
- ✅ Complete operational documentation
- ✅ **UNOC Batch Operations: PRODUCTION-READY!** 🚀

**Week 3 Achievement:**
```

37 minutes → 11 milliseconds
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
209,489× SPEEDUP

- Production Deployment
  = MISSION COMPLETE ✅

```

```
