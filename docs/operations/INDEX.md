# Operations Documentation Index

**Last Updated:** 2025-10-04  
**Purpose:** Operational guides, runbooks, and deployment documentation

---

## 🚀 **Getting Started**

### **1. [runbook.md](runbook.md)** — **Operational Runbook**

- Common operational tasks
- Troubleshooting guides
- Service management

### **2. [prometheus-grafana-setup.md](prometheus-grafana-setup.md)** — **Monitoring (AKTIV)** ✅

- **Prometheus:** Metrics collection setup
- **Grafana:** Dashboard configuration
- **Go Traffic Engine:** `/metrics` endpoint
- Alert rules for congestion/device status
- **Status:** Active in production

---

## 📋 **Planning & Process**

### **Planning**

- **[planning/Priorities.md](planning/Priorities.md)**
  - Feature prioritization
  - Roadmap planning
  - Resource allocation

### **Process**

- **[process/Definition-of-Done.md](process/Definition-of-Done.md)**
  - Quality gates
  - Code review checklist
  - Testing requirements
  - Documentation requirements

---

## 🏗️ **Bootstrap & Setup**

### **[bootstrap/bootstrap_anchors.md](bootstrap/bootstrap_anchors.md)**

- Initial setup procedures
- Anchor data seeding
- Configuration templates

---

## 🔧 **Go Services Operations** _(Week 1-3 Deliverables)_

### **[GO-SERVICES-DEPLOYMENT.md](GO-SERVICES-DEPLOYMENT.md)** _(TODO: Week 3)_

- **Service Deployment Guide**
- Docker/systemd configuration
- Health checks and monitoring
- Rolling updates
- Services:
  - Traffic Engine (DONE ✅)
  - Optical Compute Service (Week 2)
  - Status Propagation Service (Week 2)
  - Batch Operations Service (Week 3)

### **[GO-SERVICES-TROUBLESHOOTING.md](GO-SERVICES-TROUBLESHOOTING.md)** _(TODO: Week 3)_

- Common issues and solutions
- Log analysis
- Performance debugging
- gRPC connection troubleshooting

---

## 📊 **Monitoring Stack**

### **Active Monitoring (Prometheus + Grafana)** ✅

**Components:**

1. **Prometheus**

   - Scrapes `/metrics` from Go Traffic Engine
   - Stores time-series data
   - Alert evaluation

2. **Grafana**
   - Visualizes traffic metrics
   - Device status dashboards
   - Congestion alerts
   - Optical signal quality

**Key Metrics:**

- Traffic tick latency (target: <500ms, current: 300ms ✅)
- Congestion events
- Device status transitions
- Optical signal power/margin
- Link utilization

**Setup Guide:** [prometheus-grafana-setup.md](prometheus-grafana-setup.md)

---

## 🔗 **Related Documentation**

- **[../roadmap/OPERATION-STABLE-FOUNDATION.md](../roadmap/OPERATION-STABLE-FOUNDATION.md)** — 3-week hybrid migration plan
- **[../architecture/HYBRID-ARCHITECTURE.md](../architecture/HYBRID-ARCHITECTURE.md)** _(TODO: Week 1)_ — Go Hybrid design
- **[../performance/INDEX.md](../performance/INDEX.md)** — Performance benchmarks
- **[../setup/local-dev.md](../setup/local-dev.md)** — Development environment

---

## 🚨 **Alerts & Incident Response**

### **Critical Alerts** (Prometheus rules)

1. **Traffic Tick Latency > 2s** (3 consecutive)

   - **Action:** Check Go engine logs, verify DB connectivity
   - **Escalate:** If persists >5 minutes

2. **Congestion Detected**

   - **Action:** Review traffic patterns, check link capacity
   - **Escalate:** If >80% links congested

3. **Device Status Degraded**

   - **Action:** Check reachability, verify optical signal
   - **Escalate:** If multiple devices affected

4. **Optical Signal Loss** (RX power < -28 dBm)
   - **Action:** Inspect fiber, check ONT placement
   - **Escalate:** If ONT unreachable >15 minutes

---

## 📦 **Deployment Checklist**

### **Pre-Deployment:**

- [ ] Run full test suite (`pytest -q`)
- [ ] Check for lint errors (`ruff check .`)
- [ ] Verify database migrations (`alembic current`)
- [ ] Review performance metrics (last 24h)

### **Deployment:**

- [ ] Backup database (if schema changes)
- [ ] Stop Go Traffic Engine (graceful shutdown)
- [ ] Deploy new Go services (if applicable)
- [ ] Apply database migrations
- [ ] Start Go Traffic Engine
- [ ] Verify `/metrics` endpoint responding
- [ ] Check Grafana dashboards (traffic resuming)

### **Post-Deployment:**

- [ ] Monitor traffic tick latency (target: <500ms)
- [ ] Verify device status updates
- [ ] Check for errors in logs
- [ ] Run smoke tests (create device, create link)
- [ ] Update deployment notes

---

## 🛠️ **Tools & Scripts**

### **Database Management:**

```bash
# Reset dev database
python scripts/reset_dev_db.py --force --seed

# Apply migrations
alembic upgrade head

# Check current schema version
alembic current
```

### **Go Service Management:**

```bash
# Start Go Traffic Engine
cd engine-go
go build -o traffic-engine.exe ./cmd/traffic-engine
./traffic-engine.exe

# Check if running
Get-Process -Name "traffic-engine"

# View logs (if using systemd)
journalctl -u traffic-engine -f
```

### **Backend Service:**

```bash
# Start FastAPI backend
python run.py

# Or use VS Code task: "backend: run"
```

---

**Note:** Prometheus/Grafana monitoring is **ACTIVE** in production. Do not disable or remove without coordinated migration plan.
