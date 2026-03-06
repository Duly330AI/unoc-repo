"""Splitter utilities: default port model and usage counting.

V1 semantics:
- Default 1:N with N=32 (1 IN, N OUT ports) when no hardware model is provided.
- ports_used = number of OUT ports that have at least one ONT/BUSINESS_ONT downstream
- downstream_onts = count of unique ONTs reachable across all OUT ports

Traversal is deterministic and limited: start from each OUT interface, walk links across
devices until an ONT/BUSINESS_ONT is found or no further neighbors exist. Passive inline
devices (ODF/NVT/SPLITTER/HOP) are transparent.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable

from sqlmodel import Session, select

from backend.models import Device, DeviceType, Interface, Link

DEFAULT_SPLIT_RATIO = 32


def ensure_default_ports_for_splitter(
    session: Session, splitter: Device, ratio: int | None = None
) -> None:
    """Idempotently create 1 IN + N OUT ports on a SPLITTER when not provided by catalog.

    Does not remove existing ports. If ports already exist, only missing ones are added.
    """
    if splitter.type != DeviceType.SPLITTER:
        return
    n = int(ratio or DEFAULT_SPLIT_RATIO)
    # Load existing names to avoid duplicates
    ifaces = session.exec(select(Interface).where(Interface.device_id == splitter.id)).all()
    names = {i.name for i in ifaces}
    # Create IN if missing
    if "in" not in names:
        session.add(Interface(id=f"{splitter.id}-in", device_id=splitter.id, name="in"))
    # Create OUT_1..OUT_N
    for idx in range(1, n + 1):
        nm = f"out{idx}"
        if nm not in names:
            session.add(Interface(id=f"{splitter.id}-{nm}", device_id=splitter.id, name=nm))
    # Commit is handled by caller


def _iter_counterparts(links_by_if: dict[str, list[Link]], if_id: str) -> Iterable[str]:
    for ln in links_by_if.get(if_id, []):
        if ln.a_interface_id == if_id:
            yield ln.b_interface_id
        elif ln.b_interface_id == if_id:
            yield ln.a_interface_id


def compute_splitter_usage(session: Session, splitter: Device) -> tuple[int, int, int]:
    """Return (ports_total, ports_used, downstream_onts) for the given SPLITTER device.

    OUT ports are interfaces whose name starts with 'out'. If none match, we treat all
    non-'in' interfaces as OUT to be tolerant to legacy data.
    """
    if splitter.type != DeviceType.SPLITTER:
        return (0, 0, 0)
    # Load splitter interfaces
    s_ifaces = session.exec(select(Interface).where(Interface.device_id == splitter.id)).all()
    out_ifaces = [i for i in s_ifaces if str(i.name).lower().startswith("out")]
    if not out_ifaces:
        out_ifaces = [i for i in s_ifaces if str(i.name).lower() != "in"]
    ports_total = len(out_ifaces)
    if ports_total == 0:
        return (0, 0, 0)
    # Build link adjacency once
    links = session.exec(select(Link)).all()
    links_by_if: dict[str, list[Link]] = {}
    for ln in links:
        links_by_if.setdefault(ln.a_interface_id, []).append(ln)
        links_by_if.setdefault(ln.b_interface_id, []).append(ln)
    # Preload interface -> device map for all interfaces referenced in links to avoid N+1
    iface_ids = {iid for iid in links_by_if.keys()}
    if iface_ids:
        ifrows = session.exec(
            select(Interface).where(Interface.id.in_(list(iface_ids)))  # type: ignore[attr-defined]
        ).all()
    else:
        ifrows = []
    dev_by_if = {i.id: i.device_id for i in ifrows}
    # Also include splitter's own interfaces
    for i in s_ifaces:
        dev_by_if.setdefault(i.id, splitter.id)
    # Preload device types for speed
    dev_ids = set(dev_by_if.values())
    if dev_ids:
        drows = session.exec(
            select(Device).where(Device.id.in_(list(dev_ids)))  # type: ignore[attr-defined]
        ).all()
    else:
        drows = []
    dtype_by_dev = {d.id: d.type for d in drows}

    def has_ont_reachable(start_if: Interface) -> tuple[bool, set[str]]:
        visited: set[str] = set()
        q: deque[str] = deque([start_if.id])
        seen_onts: set[str] = set()
        while q:
            cur_if = q.popleft()
            if cur_if in visited:
                continue
            visited.add(cur_if)
            for nb_if in _iter_counterparts(links_by_if, cur_if):
                if nb_if in visited:
                    continue
                nb_dev = dev_by_if.get(nb_if)
                if not nb_dev:
                    continue
                t = dtype_by_dev.get(nb_dev)
                if t in {DeviceType.ONT, DeviceType.BUSINESS_ONT}:
                    seen_onts.add(nb_dev)
                q.append(nb_if)
        return (len(seen_onts) > 0, seen_onts)

    ports_used = 0
    global_onts: set[str] = set()
    for out_if in out_ifaces:
        used, onts = has_ont_reachable(out_if)
        if used:
            ports_used += 1
        global_onts.update(onts)
    return (ports_total, ports_used, len(global_onts))


def find_out_interface_reaching(
    session: Session, splitter: Device, target_interface_id: str
) -> Interface | None:
    """Return the OUT interface on the splitter whose path can reach target_interface_id.

    Uses current topology (no side effects). If no OUT can reach the target, returns None.
    """
    if splitter.type != DeviceType.SPLITTER:
        return None
    # Splitter interfaces
    s_ifaces = session.exec(select(Interface).where(Interface.device_id == splitter.id)).all()
    out_ifaces = [i for i in s_ifaces if str(i.name).lower().startswith("out")]
    if not out_ifaces:
        out_ifaces = [i for i in s_ifaces if str(i.name).lower() != "in"]
    if not out_ifaces:
        return None
    # Build adjacency once
    links = session.exec(select(Link)).all()
    links_by_if: dict[str, list[Link]] = {}
    for ln in links:
        links_by_if.setdefault(ln.a_interface_id, []).append(ln)
        links_by_if.setdefault(ln.b_interface_id, []).append(ln)

    def _reaches(start_if: Interface, goal_if_id: str) -> bool:
        visited: set[str] = set()
        q: deque[str] = deque([start_if.id])
        while q:
            cur = q.popleft()
            if cur == goal_if_id:
                return True
            if cur in visited:
                continue
            visited.add(cur)
            for nb_if in _iter_counterparts(links_by_if, cur):
                if nb_if not in visited:
                    q.append(nb_if)
        return False

    for out_if in out_ifaces:
        if _reaches(out_if, target_interface_id):
            return out_if
    return None


def out_interface_has_ont(session: Session, out_interface_id: str) -> bool:
    """Check if any ONT-family device is reachable from the provided out interface.

    Assumes the interface belongs to a SPLITTER. Safe for any interface id; returns False if
    graph or types are incomplete.
    """
    # Build adjacency
    links = session.exec(select(Link)).all()
    links_by_if: dict[str, list[Link]] = {}
    for ln in links:
        links_by_if.setdefault(ln.a_interface_id, []).append(ln)
        links_by_if.setdefault(ln.b_interface_id, []).append(ln)
    # Preload interface -> device
    iface_ids = set(links_by_if.keys())
    if iface_ids:
        ifrows = session.exec(
            select(Interface).where(Interface.id.in_(list(iface_ids)))  # type: ignore[attr-defined]
        ).all()
    else:
        ifrows = []
    dev_by_if = {i.id: i.device_id for i in ifrows}
    # Preload device types
    dev_ids = set(dev_by_if.values())
    if dev_ids:
        drows = session.exec(
            select(Device).where(Device.id.in_(list(dev_ids)))  # type: ignore[attr-defined]
        ).all()
    else:
        drows = []
    dtype_by_dev = {d.id: d.type for d in drows}

    visited: set[str] = set()
    q: deque[str] = deque([out_interface_id])
    while q:
        cur_if = q.popleft()
        if cur_if in visited:
            continue
        visited.add(cur_if)
        for nb_if in _iter_counterparts(links_by_if, cur_if):
            if nb_if in visited:
                continue
            nb_dev = dev_by_if.get(nb_if)
            if not nb_dev:
                continue
            t = dtype_by_dev.get(nb_dev)
            if t in {DeviceType.ONT, DeviceType.BUSINESS_ONT}:
                return True
            q.append(nb_if)
    return False
