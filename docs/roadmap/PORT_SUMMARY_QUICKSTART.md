# Port Summary Service - Quick Start Guide

Fast O(1) port occupancy queries. **50-100× speedup** over Python!

---

## 🚀 **5-Minute Setup**

### **Step 1: Start the Service**

```powershell
# Terminal 1: Start Port Summary Service
cd C:\noc_project\UNOC\unoc\engine-go\cmd\port-summary-service

$env:DATABASE_URL="postgresql://unoc:unocpw@localhost:5432/unocdb?sslmode=disable"
$env:PORT="50054"
.\port-summary-service.exe
```

**Expected Output**:

```
✅ Loaded 113 devices, 368 interfaces, 112 links in 5.6ms
✅ Found 83 ONT devices, computed optical paths for 83 ONTs
✅ Port Summary Service listening on port 50054
```

### **Step 2: Generate Python Proto Files** (One-Time)

```powershell
# From repo root
cd engine-go

# Generate Python gRPC code
python -m grpc_tools.protoc `
    --python_out=../backend/proto `
    --grpc_python_out=../backend/proto `
    --proto_path=proto `
    proto/port_summary/port_summary.proto
```

**Result**: Creates `backend/proto/port_summary/port_summary_pb2.py` and `*_grpc.py`

### **Step 3: Enable in Python Backend**

```python
# In your .env or environment
USE_PORT_SUMMARY_SERVICE=1
PORT_SUMMARY_SERVICE_HOST=localhost
PORT_SUMMARY_SERVICE_PORT=50054
```

### **Step 4: Use in FastAPI**

```python
from backend.clients.port_summary_client import get_port_summary_client

@router.get("/devices/{device_id}/ports")
async def get_device_ports(device_id: str):
    client = get_port_summary_client()

    # Fast query (5-10ms instead of 250-700ms!)
    summary = await client.get_port_summary(device_id)

    if summary is None:
        # Graceful fallback if service unavailable
        summary = compute_ports_legacy(device_id)

    return {"device_id": device_id, **summary}
```

---

## 📊 **What You Get**

### **Before (Python Direct DB)**

```python
# Slow: 250-700ms per request
def get_olt_port_summary(olt_id):
    interfaces = db.query(Interface).filter_by(device_id=olt_id).all()
    for iface in interfaces:
        if iface.port_role == "PON":
            # 💥 Scans 10,000+ ONT rows!
            count = db.query(Device).filter(
                Device.type == "ONT",
                Device.provisioned == True,
                ... complex join conditions ...
            ).count()
```

### **After (Go Service)**

```python
# Fast: 5-10ms per request
summary = await client.get_port_summary(olt_id)
# All data precomputed in memory!
# Result: {
#     "interfaces": [
#         {
#             "id": "pon1-uuid",
#             "name": "PON1",
#             "port_role": "PON",
#             "occupancy": 42,  ← O(1) lookup!
#             "capacity": 128
#         }
#     ]
# }
```

**Speedup**: 50-100× faster! 🚀

---

## 🧪 **Testing**

### **Health Check**

```python
from backend.clients.port_summary_client import get_port_summary_client

client = get_port_summary_client()

if client.is_available():
    print("✅ Service connected!")
else:
    print("⚠️ Service unavailable, will use fallback")
```

### **Get Port Summary**

```python
# Single device
summary = await client.get_port_summary("olt-uuid-here")

# Bulk (30 devices in one call!)
summaries = await client.get_bulk_port_summary([
    "olt-1", "olt-2", "olt-3", ...
])
```

### **Expected Response**

```json
{
  "interfaces": [
    {
      "id": "interface-uuid",
      "name": "PON1",
      "port_role": "PON",
      "effective_status": "up",
      "occupancy": 42,
      "capacity": 128
    },
    {
      "id": "interface-uuid-2",
      "name": "ge0/0/1",
      "port_role": "ACCESS",
      "effective_status": "up",
      "occupancy": 1,
      "capacity": 1
    }
  ]
}
```

---

## 🔧 **Troubleshooting**

### **Service Won't Start**

**Error**: `Failed to ping database: pq: SSL is not enabled`  
**Fix**: Add `?sslmode=disable` to DATABASE_URL

**Error**: `column "effective_status" does not exist`  
**Fix**: Service uses `admin_status` field (already fixed in v1.0)

**Error**: `Port 50054 already in use`  
**Fix**: Kill existing process:

```powershell
Get-Process | Where-Object { $_.ProcessName -eq "port-summary-service" } | Stop-Process -Force
```

### **Python Client Issues**

**Error**: `Import "backend.proto.port_summary" could not be resolved`  
**Fix**: Generate proto files (Step 2 above)

**Warning**: `Port Summary Service unavailable`  
**Fix**: Check service is running on port 50054

### **Performance Not Improved**

**Check 1**: Is service actually being called?

```python
client = get_port_summary_client()
print(f"Service available: {client.is_available()}")
```

**Check 2**: Are you using the client in your endpoints?

```python
# Make sure you're calling client.get_port_summary()
# Not the old direct DB queries!
```

---

## 📈 **Monitoring**

### **Service Logs**

```
2025/10/08 16:05:32 Starting Port Summary Service...
2025/10/08 16:05:32 Database connection established
2025/10/08 16:05:32 Loading initial state from database...
2025/10/08 16:05:32 Found 83 ONT devices, computed optical paths for 83 ONTs
2025/10/08 16:05:32 Computed PON occupancy: 83 ONTs across 2 PON ports on 1 OLTs
2025/10/08 16:05:32 Loaded 113 devices, 368 interfaces, 112 links in 5.6ms
2025/10/08 16:05:32 Port Summary Service listening on port 50054
```

**Key Metrics**:

- Load time: **5-10ms** ✅
- ONT count: Should match your provisioned ONTs
- PON ports: Should match your OLT configuration

### **Python Client Logs**

```python
import logging
logging.basicConfig(level=logging.INFO)

# Will log:
# INFO: ✅ Port Summary Service connected: localhost:50054
# or
# WARNING: ⚠️ Port Summary Service unavailable (localhost:50054): ...
```

---

## 🎯 **Next Steps**

1. **Start Service** - Follow Step 1 above
2. **Generate Protos** - Follow Step 2 (one-time)
3. **Test Connection** - Use health check code
4. **Integrate Endpoint** - Update your device ports API
5. **Measure Performance** - Compare before/after response times
6. **Monitor** - Check logs for errors

---

## 📚 **Full Documentation**

- Architecture: [PORT_SUMMARY_PHASE1_COMPLETE.md](./PORT_SUMMARY_PHASE1_COMPLETE.md)
- Proto Definition: `engine-go/proto/port_summary/port_summary.proto`
- Python Client: `backend/clients/port_summary_client.py`
- Tests: `engine-go/cmd/port-summary-service/*_test.go`

---

**Questions?** Check the main documentation or service logs!

**Performance Issues?** Make sure service is running and client is connected.

**Ready for Production?** See Phase 2 (Event-Driven Updates) in main docs.
