from __future__ import annotations

from collections.abc import Iterable

from backend.models import Interface, Link, Status


def build_adjacency(
    ifaces: Iterable[Interface],
    links: Iterable[Link],
    is_link_passable,
    device_override_map: dict[str, Status | None],
):
    """Build adjacency and mappings for passable links.

    PERF-002: Inline link status evaluation using preloaded device overrides.
    Rules:
    - Admin override on link wins if set (UP/DOWN/BLOCKING as forced)
    - Otherwise check endpoint device overrides; if either is DOWN → link DOWN
    - Otherwise use stored link.status

    Returns a tuple of (device_neighbors, link_by_pair, iface_to_device).
    """
    iface_to_device: dict[str, str] = {i.id: i.device_id for i in ifaces}
    device_neighbors: dict[str, set[str]] = {}
    link_by_pair: dict[frozenset[str], str] = {}

    for ln in links:
        try:
            if not is_link_passable(ln):
                continue

            # PERF-002: Inline link status evaluation (no DB queries!)
            eff = ln.status  # Default to stored status
            if getattr(ln, "admin_override_status", None) is not None:
                eff = ln.admin_override_status  # type: ignore[assignment]
            else:
                # Check endpoint device overrides
                a_dev_id = iface_to_device.get(ln.a_interface_id)
                b_dev_id = iface_to_device.get(ln.b_interface_id)
                if a_dev_id and device_override_map.get(a_dev_id) == Status.DOWN:
                    eff = Status.DOWN
                elif b_dev_id and device_override_map.get(b_dev_id) == Status.DOWN:
                    eff = Status.DOWN

            if eff != Status.UP:
                continue
        except Exception:
            if getattr(ln, "status", None) != Status.UP:
                continue

        a_dev = iface_to_device.get(ln.a_interface_id)
        b_dev = iface_to_device.get(ln.b_interface_id)
        if not a_dev or not b_dev:
            continue
        device_neighbors.setdefault(a_dev, set()).add(b_dev)
        device_neighbors.setdefault(b_dev, set()).add(a_dev)
        link_by_pair[frozenset({a_dev, b_dev})] = ln.id

    return device_neighbors, link_by_pair, iface_to_device
