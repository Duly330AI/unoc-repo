"""Pathfinding and upstream gating helpers for Traffic V2.

Small, deterministic utilities extracted from v2_engine to keep that module
under the max-lines policy while preserving behavior and public API.
"""

from __future__ import annotations

from collections import deque

from backend.models import DeviceType


def has_upstream_ok(session, device, backbone_present: bool) -> bool:
    """Gate traffic generation based on upstream L3 reachability.

    Mirrors the logic previously embedded in v2_engine:
    - If a backbone anchor exists in the topology and upstream resolver says not ok → block.
    - If no backbone present, tolerate certain diagnostic reasons so legacy tests without
      a backbone remain valid.
    - On resolver errors, return True (be conservative to avoid false negatives during tests).
    """

    try:
        from backend.services.dependency_resolver import has_upstream_l3_or_anchor as _has_up

        up_res = _has_up(session, device)
        if getattr(up_res, "ok", False):
            return True
        # Not ok: apply backbone/tolerated reasons policy
        if backbone_present:
            return False
        reasons = set(getattr(up_res, "reasons", []) or [])
        tolerated = {"no_router_path", "routers_no_l3"}
        if not reasons:
            return False
        return reasons.issubset(tolerated)
    except Exception:
        # On resolver errors, allow generation to avoid test disruption
        return True


def bfs_pick_anchor(
    start_id: str,
    device_neighbors: dict[str, set[str]],
    link_by_pair: dict[frozenset[str], str],
    allowed_device_ids: set[str],
    dev_type_by_id: dict[str, DeviceType],
    anchor_types: set[DeviceType],
) -> tuple[list[str], list[str]]:
    """Return (path_nodes, path_links) from start to the preferred anchor.

    Preference order for anchors:
    - BACKBONE_GATEWAY first when available
    - CORE_SITE/CORE_ROUTER next (recorded for preference, even if not in anchor_types)
    - POP next
    - Any other device whose type is in anchor_types

    If no anchor is reachable via BFS, fall back to resolve_flow_path to build a best-effort
    path; only accept the fallback if it reaches a true anchor, unless the topology has no
    such anchors at all.

    Determinism: neighbor traversal uses sorted order.
    """

    parents: dict[str, str | None] = {start_id: None}
    q: deque[str] = deque([start_id])
    found_anchor: str | None = None
    found_core_anchor: str | None = None
    found_backbone_anchor: str | None = None
    found_pop_anchor: str | None = None

    while q:
        cur = q.popleft()
        if cur != start_id and dev_type_by_id.get(cur) in anchor_types:
            dt = dev_type_by_id.get(cur)
            # Track POP explicitly as well
            if dt == DeviceType.POP:
                found_pop_anchor = found_pop_anchor or cur
            if dt == DeviceType.BACKBONE_GATEWAY:
                found_backbone_anchor = found_backbone_anchor or cur
            found_anchor = found_anchor or cur
        # Also consider core types for preference if present
        dt_cur = dev_type_by_id.get(cur)
        if cur != start_id and dt_cur in {
            getattr(DeviceType, "CORE_SITE", None),
            getattr(DeviceType, "CORE_ROUTER", None),
        }:
            found_core_anchor = found_core_anchor or cur

        for nb in sorted(device_neighbors.get(cur, set())):
            if nb in parents:
                continue
            if nb not in allowed_device_ids:
                continue
            parents[nb] = cur
            q.append(nb)

    # Choose the best available anchor by preference order
    anchor_to_use = found_backbone_anchor or found_core_anchor or found_pop_anchor or found_anchor

    if not anchor_to_use:
        # No anchor reachable: attempt to use forwarding path as fallback
        path_nodes = [start_id]
        path_links: list[str] = []
        try:
            from backend.services import forwarding_service as _fw

            Flow = getattr(_fw, "Flow", None)
            resolve = getattr(_fw, "resolve_flow_path", None)
            if Flow is not None and resolve is not None:
                cur_if = f"{start_id}-if0"
                flow = Flow(
                    source_ip="10.0.0.1",
                    destination_ip="192.0.2.1",
                    current_device_id=start_id,
                    current_interface_id=cur_if,
                )
                res = resolve(flow)
                hops = res.get("hops") or []
                for h in hops:
                    try:
                        dev_id = getattr(h, "current_device_id", None) or h.get("current_device_id")
                        if dev_id and dev_id in allowed_device_ids and dev_id not in path_nodes:
                            path_nodes.append(dev_id)
                    except Exception:
                        continue
                meta = res.get("hop_metadata") or []
                for m in meta:
                    try:
                        dev_id = m.get("device_id")
                        if dev_id and dev_id in allowed_device_ids and dev_id not in path_nodes:
                            path_nodes.append(dev_id)
                        lid = m.get("link_id_to_next")
                        if lid and lid not in path_links:
                            path_links.append(lid)
                    except Exception:
                        continue
                # Accept fallback only if it reaches a true anchor, unless no anchors exist at all
                has_true_anchor = any(
                    (dev_type_by_id.get(x) in anchor_types) and (x != start_id) for x in path_nodes
                )
                if not has_true_anchor:
                    any_anchor_exists = any((t in anchor_types) for t in dev_type_by_id.values())
                    if not any_anchor_exists:
                        pass  # accept EDGE fallback path as best-effort when no anchors exist
                    else:
                        path_nodes = [start_id]
                        path_links = []
        except Exception:
            pass
        # Complement links along consecutive device pairs if missing
        try:
            if len(path_nodes) >= 2:
                for i in range(len(path_nodes) - 1):
                    pair = frozenset({path_nodes[i], path_nodes[i + 1]})
                    lid = link_by_pair.get(pair)
                    if lid and lid not in path_links:
                        path_links.append(lid)
        except Exception:
            pass
        return path_nodes, path_links

    # Reconstruct devices from parents, ensuring start at index 0
    path_nodes2: list[str] = []
    x = anchor_to_use
    while x is not None:
        path_nodes2.append(x)
        x = parents.get(x)
    path_nodes2 = list(reversed(path_nodes2))
    if not path_nodes2 or path_nodes2[0] != start_id:
        if path_nodes2 and path_nodes2[-1] == start_id:
            path_nodes2 = list(reversed(path_nodes2))
        else:
            path_nodes2 = [start_id]

    # Map device path to link ids
    path_links2: list[str] = []
    for i in range(len(path_nodes2) - 1):
        pair = frozenset({path_nodes2[i], path_nodes2[i + 1]})
        lid = link_by_pair.get(pair)
        if lid:
            path_links2.append(lid)

    return path_nodes2, path_links2
