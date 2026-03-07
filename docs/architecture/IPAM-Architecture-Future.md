# IPAM Architecture: Current State & Future Evolution

**Date:** 2025-10-04  
**Status:** 🔮 **FUTURE DESIGN** (Architecture Exploration)  
**Context:** Lessons learned from HGO-011 (IP pool exhaustion at 254 ONTs)

---

## 🎯 Executive Summary

This document explores **production-grade IPAM architecture** for telecom networks, addressing the limitations discovered during HGO-011 testing. We analyze 3 approaches:

1. **Static Prefixes (CURRENT)** - Simple but limited to hardcoded pools
2. **Hierarchical Prefixes (RECOMMENDED)** - Region/Site/POP-based allocation
3. **Dynamic Pool Expansion (ADVANCED)** - Auto-create new /24 blocks on demand

**Key Insight from HGO-011:**

- ❌ **Problem:** Hardcoded `/24` prefix (254 IPs) exhausted at ONT #254
- ✅ **Fix:** Changed `ont_mgmt` to `/16` (65,534 IPs) for enterprise scale
- ⚠️ **Limitation:** Still uses ONE static prefix per device role (doesn't scale to multi-region)

---

## 📊 Current Architecture (Static Prefixes)

### Implementation (as of HGO-011)

```python
# backend/services/seed_helpers/ipam.py
def ensure_ipam_defaults(session: Session):
    """Create ONE prefix per device role (static allocation)."""
    desired = {
        "core_mgmt":  "10.252.0.0/24",  # Core/Edge routers: 254 IPs
        "olt_mgmt":   "10.251.0.0/24",  # OLT devices: 254 IPs
        "ont_mgmt":   "10.250.0.0/16",  # ONT devices: 65,534 IPs ← Fixed in HGO-011
        "aon_mgmt":   "10.253.0.0/24",  # AON switches: 254 IPs
        "cpe_mgmt":   "10.254.0.0/24",  # CPE devices: 254 IPs
        "noc_tools":  "10.250.10.0/24", # NOC tools: 254 IPs
    }
    # ONE Prefix object per role, stored in DB
```

### Device Provisioning Flow

```python
# backend/services/provisioning_ipam.py
def classify_prefix_role(device_type: DeviceType):
    """Map device type → prefix role (1:1 mapping)."""
    return {
        DeviceType.CORE_ROUTER: "core_mgmt",  # ALL cores → SAME /24
        DeviceType.EDGE_ROUTER: "core_mgmt",  # ALL edges → SAME /24
        DeviceType.OLT:         "olt_mgmt",   # ALL OLTs  → SAME /24
        DeviceType.ONT:         "ont_mgmt",   # ALL ONTs  → SAME /16
    }.get(device_type)

def next_free_ip_in_prefix(session, prefix: Prefix):
    """Allocate next free IP from the prefix (linear scan)."""
    net = ipaddress.ip_network(prefix.prefix)  # e.g., 10.252.0.0/24
    for host in net.hosts():  # 10.252.0.1, 10.252.0.2, ..., 10.252.0.254
        if not taken:
            return str(host), net.prefixlen
    return None  # POOL_EXHAUSTED if all IPs allocated
```

### Capacity Limits (Current)

| Device Role | Prefix        | Max Devices | Notes                          |
| ----------- | ------------- | ----------- | ------------------------------ |
| Core/Edge   | 10.252.0.0/24 | **254**     | ⚠️ Hard limit (no auto-expand) |
| OLT         | 10.251.0.0/24 | **254**     | ⚠️ Hard limit                  |
| **ONT**     | 10.250.0.0/16 | **65,534**  | ✅ Fixed in HGO-011            |
| AON Switch  | 10.253.0.0/24 | **254**     | ⚠️ Hard limit                  |
| CPE         | 10.254.0.0/24 | **254**     | ⚠️ Hard limit                  |

### Limitations

1. **No Multi-Region Support**

   - All Core routers in ALL regions share ONE `/24` prefix
   - Cannot isolate `Core-Region1` (10.252.0.x) from `Core-Region2` (10.252.1.x)

2. **No Dynamic Expansion**

   - Hitting 254 Core routers → POOL_EXHAUSTED (no auto-create next /24)
   - Manual intervention required (add new Prefix to DB)

3. **No Hierarchy**

   - Cannot model `Region → Site → POP → Device` relationships
   - All devices at same "flat" level

4. **No IP Reclamation**
   - Deleting a device doesn't return IP to pool (orphaned InterfaceAddress rows)
   - Manual cleanup required

---

## 🏗️ Approach A: Multi-Region Static Prefixes (Simple Evolution)

**Goal:** Support multiple regions with dedicated prefixes per role per region.

### Database Schema Changes

```python
# NEW: Add 'region' field to Prefix model
class Prefix(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    prefix: str = Field(index=True)  # e.g., "10.252.0.0/24"
    vrf_id: int = Field(foreign_key="vrf.id")
    description: str | None = None  # e.g., "core_mgmt"
    region: str | None = None        # 🆕 e.g., "west", "east", "central"

# NEW: Add 'region' field to Device model (optional)
class Device(SQLModel, table=True):
    # ... existing fields ...
    region: str | None = None  # 🆕 Device's region (for prefix selection)
```

### Seeding Logic (Multi-Region)

```python
# backend/services/seed_helpers/ipam.py (ENHANCED)
def ensure_ipam_defaults(session: Session):
    """Create prefixes for multiple regions."""
    mgmt_vrf = get_or_create_vrf(session, "mgmt")

    # Define prefixes per region
    regions = ["west", "east", "central"]  # Configurable

    for region in regions:
        prefixes = [
            # Core/Edge: /24 per region (254 devices each)
            Prefix(
                prefix=f"10.252.{regions.index(region)}.0/24",
                vrf_id=mgmt_vrf.id,
                description="core_mgmt",
                region=region,
            ),
            # OLT: /24 per region
            Prefix(
                prefix=f"10.251.{regions.index(region)}.0/24",
                vrf_id=mgmt_vrf.id,
                description="olt_mgmt",
                region=region,
            ),
            # ONT: /16 per region (65k devices each)
            Prefix(
                prefix=f"10.250.{regions.index(region) * 16}.0/16",
                vrf_id=mgmt_vrf.id,
                description="ont_mgmt",
                region=region,
            ),
        ]
        for p in prefixes:
            session.add(p)
    session.commit()
```

### Provisioning Logic (Region-Aware)

```python
# backend/services/provisioning_ipam.py (ENHANCED)
def find_prefix_for_device(session: Session, device: Device) -> Prefix | None:
    """Find appropriate prefix based on device type AND region."""
    role = classify_prefix_role(device.type)
    if not role:
        return None

    # Prefer region-specific prefix if device has region set
    if device.region:
        prefix = session.exec(
            select(Prefix).where(
                (Prefix.description == role) &
                (Prefix.region == device.region)
            )
        ).first()
        if prefix:
            return prefix

    # Fallback: any prefix with matching role (region=NULL)
    return session.exec(
        select(Prefix).where(
            (Prefix.description == role) &
            (Prefix.region.is_(None))  # Legacy/default region
        )
    ).first()
```

### Capacity (Multi-Region)

| Region    | Core/Edge       | OLT             | ONT              |
| --------- | --------------- | --------------- | ---------------- |
| West      | 10.252.0.0/24   | 10.251.0.0/24   | 10.250.0.0/16    |
| East      | 10.252.1.0/24   | 10.251.1.0/24   | 10.250.16.0/16   |
| Central   | 10.252.2.0/24   | 10.251.2.0/24   | 10.250.32.0/16   |
| **Total** | **762 devices** | **762 devices** | **196k devices** |

### Pros & Cons

✅ **Pros:**

- Simple extension of current architecture
- No complex hierarchy logic
- Easy to implement (add 2 columns, update seeding)
- Scales to 10+ regions easily

❌ **Cons:**

- Still manual prefix creation (no dynamic expansion)
- Flat structure (no Site/POP hierarchy)
- Hitting 254 devices per region → manual intervention

---

## 🏗️ Approach B: Hierarchical IPAM (Recommended for Telco)

**Goal:** Model real-world topology: `Region → Site → POP → Device`

### Hierarchy Model

```
Organization: "ISP XYZ"
├── Region: "West"
│   ├── Site: "Los Angeles"
│   │   ├── POP: "LA-Downtown"
│   │   │   ├── Core1 (10.252.0.1)
│   │   │   ├── OLT1  (10.251.0.1)
│   │   │   └── ONT1-100 (10.250.0.1 - .100)
│   │   └── POP: "LA-Airport"
│   │       └── ...
│   └── Site: "San Diego"
│       └── ...
└── Region: "East"
    └── ...
```

### Database Schema (Hierarchical)

```python
# NEW: Location hierarchy model
class Location(SQLModel, table=True):
    """Hierarchical location (Region/Site/POP/Rack)."""
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    type: str  # "region", "site", "pop", "rack"
    parent_id: int | None = Field(default=None, foreign_key="location.id")

    # Geospatial (optional)
    latitude: float | None = None
    longitude: float | None = None

# ENHANCED: Prefix with location assignment
class Prefix(SQLModel, table=True):
    # ... existing fields ...
    location_id: int | None = Field(foreign_key="location.id")  # 🆕

    # Hierarchical allocation strategy
    auto_allocate: bool = False  # If True, auto-create sub-prefixes

# ENHANCED: Device with location
class Device(SQLModel, table=True):
    # ... existing fields ...
    location_id: int | None = Field(foreign_key="location.id")  # 🆕
```

### Seeding Logic (Hierarchical)

```python
def setup_hierarchical_ipam(session: Session):
    """Create location hierarchy and assign prefixes."""
    mgmt_vrf = get_or_create_vrf(session, "mgmt")

    # 1. Create location hierarchy
    region_west = Location(name="West", type="region")
    session.add(region_west)
    session.flush()

    site_la = Location(name="Los Angeles", type="site", parent_id=region_west.id)
    session.add(site_la)
    session.flush()

    pop_la_downtown = Location(name="LA-Downtown", type="pop", parent_id=site_la.id)
    session.add(pop_la_downtown)
    session.flush()

    # 2. Assign prefixes to locations
    # Region-level prefix (supernet)
    region_prefix = Prefix(
        prefix="10.250.0.0/12",  # Supernet for entire West region
        vrf_id=mgmt_vrf.id,
        location_id=region_west.id,
        description="ont_mgmt",
        auto_allocate=True,  # Auto-create sub-prefixes for sites
    )
    session.add(region_prefix)

    # Site-level prefix (carved from region supernet)
    site_prefix = Prefix(
        prefix="10.250.0.0/16",  # LA site gets /16 (65k IPs)
        vrf_id=mgmt_vrf.id,
        location_id=site_la.id,
        description="ont_mgmt",
        auto_allocate=True,
    )
    session.add(site_prefix)

    # POP-level prefix (carved from site prefix)
    pop_prefix = Prefix(
        prefix="10.250.0.0/20",  # Downtown POP gets /20 (4k IPs)
        vrf_id=mgmt_vrf.id,
        location_id=pop_la_downtown.id,
        description="ont_mgmt",
    )
    session.add(pop_prefix)
    session.commit()
```

### Provisioning Logic (Location-Aware)

```python
def find_prefix_for_device(session: Session, device: Device) -> Prefix | None:
    """Find most specific prefix for device's location."""
    if not device.location_id:
        return None  # Fallback to legacy logic

    role = classify_prefix_role(device.type)

    # Walk up location hierarchy to find matching prefix
    location = session.get(Location, device.location_id)
    while location:
        prefix = session.exec(
            select(Prefix).where(
                (Prefix.location_id == location.id) &
                (Prefix.description == role)
            )
        ).first()
        if prefix:
            return prefix

        # Walk up to parent location
        if location.parent_id:
            location = session.get(Location, location.parent_id)
        else:
            break

    return None  # No prefix found in hierarchy
```

### Address Allocation Example

```
Device: ONT-123
Location: POP "LA-Downtown" (id=42)

Prefix Search:
1. Check POP level (LA-Downtown): 10.250.0.0/20 ✓
2. Allocate next free IP: 10.250.0.1/20
3. Done!

Device: ONT-456
Location: POP "LA-Airport" (id=43)

Prefix Search:
1. Check POP level (LA-Airport): None
2. Walk up to Site (Los Angeles): 10.250.0.0/16 ✓
3. Allocate next free IP: 10.250.16.1/16
4. Optional: Auto-create POP-level prefix (10.250.16.0/20) for future devices
```

### Pros & Cons

✅ **Pros:**

- Models real network topology (Region→Site→POP)
- Supports geo-redundancy, disaster recovery
- Prefix utilization reporting per location
- Natural fit for multi-datacenter ISPs

❌ **Cons:**

- Complex to implement (location hierarchy, prefix carving)
- Requires careful IP planning (avoid fragmentation)
- Migration from flat to hierarchical is non-trivial

---

## 🏗️ Approach C: Dynamic Pool Expansion (Auto-Create Prefixes)

**Goal:** Automatically create new `/24` blocks when current pool nears exhaustion.

### Implementation Strategy

```python
def allocate_ip_with_auto_expand(
    session: Session,
    device: Device,
    role: str,
    supernet: str = "10.252.0.0/16",  # Supernet for core_mgmt
    block_size: int = 24,  # Create /24 blocks
    threshold: float = 0.9,  # Expand at 90% utilization
) -> tuple[str, int] | None:
    """Allocate IP with automatic pool expansion."""

    # 1. Find all prefixes for this role
    prefixes = session.exec(
        select(Prefix).where(Prefix.description == role)
    ).all()

    # 2. Try to allocate from existing prefixes
    for prefix in prefixes:
        next_ip = next_free_ip_in_prefix(session, prefix)
        if next_ip:
            return next_ip

    # 3. Check if we should expand (all pools near exhaustion)
    utilization = calculate_utilization(session, prefixes)
    if utilization < threshold:
        return None  # Pools not yet exhausted, don't expand

    # 4. Auto-create next /24 block from supernet
    supernet_obj = ipaddress.ip_network(supernet)
    used_blocks = [ipaddress.ip_network(p.prefix) for p in prefixes]

    # Find next available /24 within supernet
    for subnet in supernet_obj.subnets(new_prefix=block_size):
        if subnet not in used_blocks:
            # Create new prefix
            new_prefix = Prefix(
                prefix=str(subnet),
                vrf_id=prefixes[0].vrf_id,  # Inherit VRF
                description=role,
            )
            session.add(new_prefix)
            session.flush()

            # Allocate first IP from new block
            return next_free_ip_in_prefix(session, new_prefix)

    return None  # Supernet exhausted

def calculate_utilization(session: Session, prefixes: list[Prefix]) -> float:
    """Calculate average utilization across all prefixes."""
    total_capacity = 0
    total_used = 0
    for prefix in prefixes:
        net = ipaddress.ip_network(prefix.prefix)
        capacity = net.num_addresses - 2  # Exclude network/broadcast
        used = session.exec(
            select(InterfaceAddress).where(InterfaceAddress.prefix_id == prefix.id)
        ).count()
        total_capacity += capacity
        total_used += used

    return total_used / total_capacity if total_capacity > 0 else 0.0
```

### Example Flow

```
Scenario: 250 Core routers already provisioned (utilization 98%)

Device: Core251
Role: core_mgmt

1. Query existing prefixes:
   - 10.252.0.0/24 (98% used, 5 IPs free)

2. Check utilization: 98% > 90% threshold ✓

3. Auto-expand:
   - Supernet: 10.252.0.0/16
   - Used blocks: [10.252.0.0/24]
   - Next block: 10.252.1.0/24 ← Create new Prefix

4. Allocate from new block:
   - IP: 10.252.1.1/24
   - Core251 provisioned successfully ✅

5. Future devices:
   - Core252: 10.252.1.2/24 (from new block)
   - Core253: 10.252.1.3/24
   - ...
   - Core500: 10.252.1.250/24
   - Core501: Auto-expand to 10.252.2.0/24 (new block)
```

### Pros & Cons

✅ **Pros:**

- Zero manual intervention (scales automatically)
- Efficient utilization (only create blocks when needed)
- Works with existing flat architecture
- Easy to implement (single function)

❌ **Cons:**

- Risk of prefix fragmentation (many small /24 blocks)
- No hierarchy (all blocks at same level)
- Requires careful supernet planning (avoid overlaps)
- Potential race conditions (concurrent auto-expansion)

---

## 📋 Comparison Matrix

| Feature                    | **A: Multi-Region** | **B: Hierarchical** | **C: Auto-Expand** |
| -------------------------- | ------------------- | ------------------- | ------------------ |
| **Implementation**         | ⭐⭐⭐ Simple       | ⭐ Complex          | ⭐⭐ Moderate      |
| **Scalability**            | ⭐⭐ Good           | ⭐⭐⭐ Excellent    | ⭐⭐⭐ Excellent   |
| **Multi-Region**           | ✅ Yes              | ✅ Yes              | ❌ No              |
| **Hierarchy**              | ❌ Flat             | ✅ Tree             | ❌ Flat            |
| **Manual Intervention**    | ⚠️ Medium           | ⚠️ Medium           | ✅ None            |
| **IP Efficiency**          | ⭐⭐ Good           | ⭐⭐⭐ Excellent    | ⭐⭐ Good          |
| **Migration from Current** | ⭐⭐⭐ Easy         | ⭐ Hard             | ⭐⭐⭐ Easy        |
| **Telco Best Practice**    | ⭐⭐ Partial        | ⭐⭐⭐ Full         | ⭐ Minimal         |

---

## 🎯 Recommendations

### For Current Project (UNOC)

**Phase 1: Keep Current Architecture** (✅ Done in HGO-011)

- ✅ Changed `ont_mgmt` to `/16` (65k IPs)
- ✅ Sufficient for MVP and initial deployments
- ✅ No breaking changes required

**Phase 2: Add Multi-Region Support** (Recommended for Q1 2026)

- Implement **Approach A** (simplest evolution)
- Add `region` field to Device and Prefix models
- Update seeding and provisioning logic
- Effort: 2-3 days
- **Benefit:** Scales to 10+ regions, 1000+ devices per region

**Phase 3: Consider Hierarchical IPAM** (Future, if needed)

- Implement **Approach B** only if multi-datacenter deployment required
- Full `Region → Site → POP` hierarchy
- Effort: 1-2 weeks
- **Benefit:** Enterprise-grade IPAM (NetBox/NAPALM equivalent)

**Phase 4: Optional Auto-Expansion** (Nice-to-Have)

- Implement **Approach C** for zero-touch scaling
- Effort: 1-2 days
- **Benefit:** No manual prefix management

### For Real-World ISP Deployment

**Must-Have:**

- ✅ **Approach B** (Hierarchical) - Models real network topology
- ✅ IP reclamation on device deletion
- ✅ Prefix utilization monitoring/alerting
- ✅ Integration with IPAM tools (NetBox, phpIPAM)

**Nice-to-Have:**

- ✅ **Approach C** (Auto-Expansion) - Reduces operational overhead
- ✅ Geo-redundancy (primary/backup prefixes per location)
- ✅ IPv6 support (dual-stack management)

---

## 🔧 Migration Path (Current → Multi-Region)

### Step 1: Add Schema Columns (No Downtime)

```python
# Alembic migration
def upgrade():
    op.add_column('prefix', sa.Column('region', sa.String(), nullable=True))
    op.add_column('device', sa.Column('region', sa.String(), nullable=True))
    op.create_index('ix_prefix_region', 'prefix', ['region'])
    op.create_index('ix_device_region', 'device', ['region'])

def downgrade():
    op.drop_index('ix_device_region')
    op.drop_index('ix_prefix_region')
    op.drop_column('device', 'region')
    op.drop_column('prefix', 'region')
```

### Step 2: Backfill Existing Data (Optional)

```python
# Mark all existing prefixes as region=NULL (legacy/default)
UPDATE prefix SET region = NULL WHERE region IS NULL;

# Optional: Assign devices to regions based on ID pattern
UPDATE device SET region = 'west' WHERE id LIKE 'ont1_%';
UPDATE device SET region = 'east' WHERE id LIKE 'ont2_%';
```

### Step 3: Update Seeding Logic

```python
# backend/services/seed_helpers/ipam.py
def ensure_ipam_defaults(session: Session, regions: list[str] | None = None):
    """Enhanced: Create prefixes for multiple regions."""
    if not regions:
        regions = [None]  # Backward compatible (single region=NULL)

    mgmt_vrf = get_or_create_vrf(session, "mgmt")

    for region in regions:
        # Create prefixes for this region
        # (See Approach A implementation above)
```

### Step 4: Update Provisioning Logic

```python
# backend/services/provisioning_ipam.py
def find_prefix_for_device(session, device):
    """Enhanced: Prefer region-specific prefix if available."""
    role = classify_prefix_role(device.type)

    # Try region-specific first
    if device.region:
        prefix = session.exec(
            select(Prefix).where(
                (Prefix.description == role) &
                (Prefix.region == device.region)
            )
        ).first()
        if prefix:
            return prefix

    # Fallback: legacy prefix (region=NULL)
    return session.exec(
        select(Prefix).where(
            (Prefix.description == role) &
            (Prefix.region.is_(None))
        )
    ).first()
```

### Step 5: Deploy and Test

```bash
# 1. Run migration
alembic upgrade head

# 2. Seed new regions
python scripts/seed_multi_region.py --regions west,east,central

# 3. Test provisioning
python scripts/build_1000_ont_topo.py --region west

# 4. Verify
curl http://localhost:5001/api/prefixes?region=west
```

---

## 📚 References

### Industry Standards

- **RFC 1918:** Private IPv4 Address Space (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)
- **RFC 6598:** Shared Address Space (100.64.0.0/10) - Carrier-Grade NAT
- **RFC 4632:** CIDR (Classless Inter-Domain Routing)

### IPAM Tools (Inspiration)

- **NetBox** (DCIM + IPAM) - [https://netbox.dev/](https://netbox.dev/)
- **phpIPAM** - Open-source IP address management
- **Infoblox** - Enterprise DNS/DHCP/IPAM solution

### Telco IPAM Patterns

- **Hierarchical Allocation:** Region → Metro → Site → POP → Rack
- **Supernet Strategy:** /12 region, /16 metro, /20 site, /24 POP
- **Prefix Tagging:** `role=mgmt`, `service=residential`, `redundancy=primary`

---

## ✅ Action Items

### Immediate (HGO-011 Follow-Up)

- [x] Document current IPAM limitations (this document)
- [x] Validate `/16` prefix works for 1000 ONTs (✅ HGO-011 PASS)
- [ ] Update TODO list: Mark HGO-011 COMPLETE, add IPAM enhancement task

### Short-Term (Q1 2026)

- [ ] Implement **Approach A** (Multi-Region Static Prefixes)
- [ ] Add Alembic migration for `region` columns
- [ ] Update seeding scripts for multi-region support
- [ ] Write integration tests (region-specific provisioning)

### Long-Term (Q2-Q3 2026)

- [ ] Evaluate **Approach B** (Hierarchical IPAM) if multi-datacenter needed
- [ ] Implement IP reclamation on device deletion
- [ ] Add prefix utilization monitoring (Prometheus metrics)
- [ ] Integrate with NetBox for external IPAM sync

---

**End of Document**
