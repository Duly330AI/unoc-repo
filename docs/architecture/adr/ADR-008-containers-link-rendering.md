# ADR-008: Container Nodes Link Rendering and Proxy Linking

Date: 2025-09-16

Status: Accepted (Containers permanently enabled)

Context

- We are introducing container nodes (POP, CORE_SITE) to group devices visually and logically.
- Links must remain faithful to true network endpoints to avoid misleading hub-and-spoke visuals.

Decision

1. Render links between real endpoints only. A link whose endpoints are inside containers must still connect device A:portX to device B:portY. Containers are purely visual groups.

2. Use proxy linking UX when a user initiates a link from a container: the UI presents eligible endpoints within the container and completes the link between the chosen devices, not the container itself.

3. Feature flags:
   - CONTAINERS are permanently enabled (flag removed)
   - CONTAINER_PROXY_LINKING: enables the proxy linking picker flow

Consequences

- Pathfinding, metrics, and status propagation remain unchanged—containers do not alter underlying topology.
- Layout engine must account for container frame boundaries to prevent visual overflow of links.
- Tests will target the UX flow (proxy picker), not topology semantics.

Alternatives Considered

- Rendering links to a container hub node: rejected due to topology distortion and maintenance overhead.

Follow-ups

- Phase 1: Implement container rendering with slot anchors from docs/container-layouts.json
- Phase 2: Add proxy linking modal and snapping behavior
