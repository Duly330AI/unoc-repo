

# 10 · Interfaces & Addresses (Deep Dive)

This document details the interface and address data model, typical API shapes, and guidance for UI consumption and testing. It complements the higher-level IPAM and status docs.

---

## 1. Goals

- Clarify shapes for interfaces (MACs, roles, admin/effective status) and addresses (IPv4).
- Outline typical endpoints and usage patterns without over-coupling to implementation details.
- Provide testing guidance for deterministic behavior (shared in-memory DB during tests).

---

## 2. Data shapes (normative fields)

### 2.1 InterfaceOut (per-device interface)

- id: string
- name: string
- mac: string
- **role: string | null (legacy InterfaceRole grouping: MANAGEMENT | P2P_UPLINK | ACCESS)**
  - **Current Usage**: The `role` field is maintained for legacy compatibility and is still serialized in API responses. It's automatically set when interfaces are created from PortProfiles with specific roles (e.g., `mgmt0` interface). The backend maintains an index on this field.
  - **Future Direction**: `port_role` is the preferred classification (ACCESS/UPLINK/PON/TRUNK) and is used for modern validations. A full deprecation of `role` has not yet been implemented.
- port_role: 'ACCESS' | 'UPLINK' | 'PON' | 'TRUNK' | null
  - This is the preferred field for interface classification and is generated from `PortProfile.port_role` during device creation.
- admin_status: 'UP' | 'DOWN'
- effective_status: 'UP' | 'DOWN' | 'DEGRADED' | 'UNKNOWN'
- addresses: AddressOut[] (may be empty)

### 2.2 AddressOut

- ip: string (IPv4 dotted)
- prefix_len: number (CIDR length)
- **primary: boolean (one primary per interface when present)**
  - **Determination**: There is no explicit API action to set the primary flag. The primary address is implicitly the first address assigned to an interface. The model comment in `backend/models.py` states: "primary flag is implicit by first address per interface in this phase; can be added later."
  - The address CRUD operations are available under `/interfaces/{interface_id}/addresses` endpoint, but there's no API to toggle the "primary" designation.
- vrf_id: number | null
- prefix_id: number | null
  (UI may resolve names via separate VRF/Prefix lookups; backend enforces uniqueness per VRF and per Prefix.)

**Multiple IP addresses per interface**:
- The model supports multiple IPv4 addresses per interface, which allows for realistic scenarios like:
  - Secondary service IPs
  - Multi-homing configurations
  - Different VRF/Prefix contexts on the same physical interface
- Addresses are independent entities with references to VRF and optionally Prefix
- The API supports multiple entries per interface

### 2.3 Interface naming conventions

- **Naming stability**: Interface names are guaranteed to be unique and stable within a device.
- **Systematic generation**: When devices are created with a HardwareModel, interfaces are deterministically generated from PortProfiles.
- **Naming scheme**:
  - For single-count ports with base names like "mgmt0", "if0", "mgmt", or "uplink", the exact name is used (possibly with a "0" suffix)
  - For multiple ports, names follow the pattern `base + index` (e.g., "pon1", "uplink2")
  - ID schema: `"{device.id}-{if_name}"`
- **Example**: The management interface is conventionally named "mgmt0"

### 2.4 MAC address generation

- **Generation mechanism**: 
  - Local OUI 02:55:4E + monotonic counter, formatted as `xx:xx:xx:xx:xx:xx`
  - Implementation: `backend/services/mac_allocator.py` (`_format_mac`, `next_mac`)
- **Initialization**: 
  - At first use, the counter is derived from the count of already assigned interface MACs in the DB state
  - Incremented for each subsequent assignment
  - Fallback strategy for determinism is described in comments
- **Uniqueness guarantee**: 
  - Global uniqueness is enforced via `Interface.mac_address` with `unique=True` 
  - And `UniqueConstraint("mac_address")` in `backend/models.py`
- **Usage**:
  - Assigned during interface creation
  - Used in automatic interface creation from PortProfiles
  - Applied in manual interface API endpoints

---

## 3. Typical API usage

- Device details fetch returns DeviceOut. Port/occupancy summaries come from `/api/ports/summary/{device_id}`. Address details are typically embedded in interface listings or exposed via a dedicated endpoint (implementation-dependent).

Stability & determinism:

- Tests use a shared in-memory SQLite and deterministic recompute ticks; UI should rely on server-provided effective_status, not recompute it client-side.
- Uniqueness constraints are enforced server-side:
  - VRF-scoped uniqueness for IPs across VRF (no duplicates in the same VRF)
  - Prefix-scoped uniqueness for IPs within a prefix

---

## 4. UI guidance

- Details panel: show MAC, role/port_role, and addresses; mark primary with a badge.
- Avoid client-side de-dup of addresses—trust server ordering and flags.
- Respect role semantics for editing (e.g., mgmt0 immutable in some flows).
- **Interface naming**: Interface names like "mgmt0", "uplink-0", "pon-1" are systematically generated during device creation based on the HardwareModel and PortProfile. These names are guaranteed to be unique and stable within a device.

---

## 5. Testing

- Backend: unit tests for multiple addresses per interface, primary selection, and VRF presence.
- Frontend: render tests for address lists; accessibility checks for screen-reader labels.

---

## 6. Cross-links

- IPAM & Status → `03_ipam_and_status.md`
- Ports & Summaries → `08_ports.md`
- Realtime & UI → `05_realtime_and_ui_model.md`