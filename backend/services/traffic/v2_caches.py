from __future__ import annotations

from collections.abc import Iterable

from sqlmodel import select

from backend.db import get_session, init_db
from backend.models import Device, DeviceType, Interface, Link, PortProfile, PortRole


def ensure_topology_caches(engine: object, dev_rows: Iterable[Device]) -> None:
    """(Re)build topology caches when PATHFINDING_STORE version changes.

    Mirrors TrafficEngine._ensure_topology_caches behavior without altering semantics.
    Mutates fields on the provided engine instance: _iface_by_id, _dev_by_iface,
    _neigh_by_if, _olt_pon_ifaces_by_olt, _dev_type_by_id, _dev_hw_model_by_id,
    _optical_path_cache, _cached_topo_version.
    """
    try:
        from backend.services.pathfinding import PATHFINDING_STORE
    except Exception:
        return

    current_v = None
    try:
        current_v = int(PATHFINDING_STORE.version())
    except Exception:
        current_v = None

    if current_v is not None and getattr(engine, "_cached_topo_version", None) == current_v:
        return

    try:
        init_db()
        with get_session() as s:
            ifaces = s.exec(select(Interface)).all()
            links = s.exec(select(Link)).all()
    except Exception:
        # On failure, keep previous caches (best-effort)
        return

    # Snapshots from devices
    try:
        dev_type_by_id = {d.id: d.type for d in dev_rows}
    except Exception:
        dev_type_by_id = {}
    try:
        dev_hw_model_by_id = {d.id: getattr(d, "hardware_model_id", None) for d in dev_rows}
    except Exception:
        dev_hw_model_by_id = {}

    iface_by_id = {i.id: i for i in ifaces}
    dev_by_if = {i.id: i.device_id for i in ifaces}

    neigh_by_if: dict[str, set[str]] = {}
    for ln in links:
        a_dev = dev_by_if.get(ln.a_interface_id)
        b_dev = dev_by_if.get(ln.b_interface_id)
        if a_dev and b_dev:
            neigh_by_if.setdefault(ln.a_interface_id, set()).add(b_dev)
            neigh_by_if.setdefault(ln.b_interface_id, set()).add(a_dev)

    olt_pon_ifaces_by_olt: dict[str, list[Interface]] = {}
    for i in ifaces:
        try:
            if getattr(i, "port_role", None) == PortRole.PON:
                did = i.device_id
                if did and dev_type_by_id.get(did) == DeviceType.OLT:
                    olt_pon_ifaces_by_olt.setdefault(did, []).append(i)
        except Exception:
            continue

    # Commit atomically
    engine._iface_by_id = iface_by_id  # type: ignore[attr-defined]
    engine._dev_by_iface = dev_by_if  # type: ignore[attr-defined]
    engine._neigh_by_if = neigh_by_if  # type: ignore[attr-defined]
    engine._olt_pon_ifaces_by_olt = {
        k: sorted(v, key=lambda x: (x.name or "")) for k, v in olt_pon_ifaces_by_olt.items()
    }  # type: ignore[attr-defined]
    engine._dev_type_by_id = dev_type_by_id  # type: ignore[attr-defined]
    engine._dev_hw_model_by_id = dev_hw_model_by_id  # type: ignore[attr-defined]
    engine._optical_path_cache = {}  # type: ignore[attr-defined]
    engine._cached_topo_version = current_v  # type: ignore[attr-defined]


def ensure_profiles_cache(engine: object) -> None:
    """Load PortProfiles grouped by hardware_model_id once.

    Mirrors TrafficEngine._ensure_profiles_cache while mutating engine._profiles_by_hw_model
    and engine._profiles_cache_ready.
    """
    if getattr(engine, "_profiles_cache_ready", False):
        return
    try:
        init_db()
        with get_session() as s:
            profs = s.exec(select(PortProfile)).all()
        by_model: dict[str, list[PortProfile]] = {}
        for p in profs:
            hm = getattr(p, "hardware_model_id", None)
            if not hm:
                continue
            by_model.setdefault(hm, []).append(p)
        engine._profiles_by_hw_model = {
            mid: sorted(lst, key=lambda x: (x.name or "")) for mid, lst in by_model.items()
        }  # type: ignore[attr-defined]
        engine._profiles_cache_ready = True  # type: ignore[attr-defined]
    except Exception:
        # Leave cache as-is (best-effort)
        pass
