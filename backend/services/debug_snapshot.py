from __future__ import annotations

import time
from collections.abc import Iterable
from typing import Any

from sqlmodel import select

from backend.db import get_session, init_db
from backend.models import (
    VRF,
    BridgeDomain,
    Device,
    DeviceType,
    Interface,
    InterfaceAddress,
    Link,
    MacAddressEntry,
    Prefix,
    Route,
    Tariff,
)
from backend.services.catalog_effective import (
    get_effective_device_capacity_mbps,
    get_effective_interface_capacity_mbps,
)
from backend.services.optical_path_resolver import resolve_optical_path
from backend.services.status_service import evaluate_device_status, evaluate_link_status
from backend.services.traffic_engine import get_v2_snapshot


def _cap(items: Iterable[Any], max_items: int | None) -> list[Any]:
    if max_items is None:
        return list(items)
    out: list[Any] = []
    for i, it in enumerate(items):
        if i >= max_items:
            break
        out.append(it)
    return out


def gather_full_snapshot(
    *,
    selected_sections: list[str] | None = None,
    max_items: int | None = None,
    include_deltas: bool = True,
) -> dict[str, Any]:
    """Collect a raw snapshot of the emulation state.

    Dev-only diagnostic; returns plain dicts, not Pydantic models.
    """
    init_db()

    want = set(
        s.lower()
        for s in (
            selected_sections
            or [
                "devices",
                "interfaces",
                "addresses",
                "links",
                "vrfs",
                "prefixes",
                "routes",
                "mac_tables",
                "metrics_v2",
                "tariffs",
                "optical",
            ]
        )
    )

    ts = time.time()
    doc: dict[str, Any] = {
        "meta": {
            "ts": ts,
            "tick": None,
            "sections": sorted(list(want)),
            "counts": {},
        }
    }

    with get_session() as s:
        if "devices" in want:
            devices = s.exec(select(Device)).all()
            dev_payload = []
            for d in _cap(devices, max_items):
                eff = evaluate_device_status(d)
                dev_payload.append(
                    {
                        "id": d.id,
                        "name": d.name,
                        "type": (d.type.value if hasattr(d.type, "value") else str(d.type)),
                        # Keep stored/raw DB status for forensics, add effective_status for truth
                        "status": (d.status.value if hasattr(d.status, "value") else str(d.status)),
                        "effective_status": (eff.value if hasattr(eff, "value") else str(eff)),
                        "provisioned": bool(getattr(d, "provisioned", False)),
                        # Expose both override and effective capacity for clarity
                        "capacity_mbps": getattr(d, "capacity", None),
                        "effective_capacity_mbps": get_effective_device_capacity_mbps(s, d),
                        "parent_container_id": getattr(d, "parent_container_id", None),
                        "hardware_model_id": getattr(d, "hardware_model_id", None),
                        "admin_override_status": (
                            d.admin_override_status.value
                            if getattr(d, "admin_override_status", None) is not None
                            and hasattr(d.admin_override_status, "value")
                            else (
                                str(d.admin_override_status)
                                if getattr(d, "admin_override_status", None) is not None
                                else None
                            )
                        ),
                    }
                )
            doc["devices"] = dev_payload
            doc["meta"]["counts"]["devices"] = len(devices)

        if "interfaces" in want:
            interfaces = s.exec(select(Interface)).all()
            if_payload = []
            for i in _cap(interfaces, max_items):
                if_payload.append(
                    {
                        "id": i.id,
                        "device_id": i.device_id,
                        "name": i.name,
                        "mac": getattr(i, "mac_address", None),
                        "role": (
                            i.role.value
                            if getattr(i, "role", None) and hasattr(i.role, "value")
                            else (str(i.role) if getattr(i, "role", None) else None)
                        ),
                        "admin_status": (
                            i.admin_status.value
                            if hasattr(i.admin_status, "value")
                            else str(i.admin_status)
                        ),
                        "capacity_mbps": getattr(i, "capacity", None),
                        "effective_capacity_mbps": get_effective_interface_capacity_mbps(s, i),
                    }
                )
            doc["interfaces"] = if_payload
            doc["meta"]["counts"]["interfaces"] = len(interfaces)

        if "tariffs" in want:
            tariffs = s.exec(select(Tariff)).all()
            t_payload = [
                {
                    "id": t.id,
                    "name": t.name,
                    "max_up_mbps": t.max_up_mbps,
                    "max_down_mbps": t.max_down_mbps,
                    "technology": (
                        t.technology.value
                        if getattr(t, "technology", None) and hasattr(t.technology, "value")
                        else (str(t.technology) if getattr(t, "technology", None) else None)
                    ),
                }
                for t in _cap(tariffs, max_items)
            ]
            doc["tariffs"] = t_payload
            doc["meta"]["counts"]["tariffs"] = len(tariffs)

        if "addresses" in want:
            addrs = s.exec(select(InterfaceAddress)).all()
            addr_payload = [
                {
                    "id": a.id,
                    "interface_id": a.interface_id,
                    "ip": a.ip,
                    "prefix_len": a.prefix_len,
                    "vrf_id": a.vrf_id,
                }
                for a in _cap(addrs, max_items)
            ]
            doc["addresses"] = addr_payload
            doc["meta"]["counts"]["addresses"] = len(addrs)

        if "links" in want:
            links = s.exec(select(Link)).all()
            link_payload = []
            for link_row in _cap(links, max_items):
                eff = evaluate_link_status(link_row)
                link_payload.append(
                    {
                        "id": link_row.id,
                        "a_interface_id": link_row.a_interface_id,
                        "b_interface_id": link_row.b_interface_id,
                        "status": (
                            link_row.status.value
                            if hasattr(link_row.status, "value")
                            else str(link_row.status)
                        ),
                        "effective_status": (eff.value if hasattr(eff, "value") else str(eff)),
                        "kind": (
                            link_row.kind.value
                            if hasattr(link_row.kind, "value")
                            else str(link_row.kind)
                        ),
                        "length_km": getattr(link_row, "length_km", None),
                        "physical_medium_id": getattr(link_row, "physical_medium_id", None),
                        "admin_override_status": (
                            link_row.admin_override_status.value
                            if getattr(link_row, "admin_override_status", None) is not None
                            and hasattr(link_row.admin_override_status, "value")
                            else (
                                str(link_row.admin_override_status)
                                if getattr(link_row, "admin_override_status", None) is not None
                                else None
                            )
                        ),
                    }
                )
            doc["links"] = link_payload
            doc["meta"]["counts"]["links"] = len(links)

        if "vrfs" in want:
            vrfs = s.exec(select(VRF)).all()
            vrf_payload = [{"id": v.id, "name": v.name} for v in _cap(vrfs, max_items)]
            doc["vrfs"] = vrf_payload
            doc["meta"]["counts"]["vrfs"] = len(vrfs)

        if "prefixes" in want:
            pfxs = s.exec(select(Prefix)).all()
            pfx_payload = [
                {"id": p.id, "vrf_id": p.vrf_id, "prefix": p.prefix, "description": p.description}
                for p in _cap(pfxs, max_items)
            ]
            doc["prefixes"] = pfx_payload
            doc["meta"]["counts"]["prefixes"] = len(pfxs)

        if "routes" in want:
            routes = s.exec(select(Route)).all()
            r_payload = [
                {
                    "id": r.id,
                    "vrf_id": r.vrf_id,
                    "prefix": r.prefix,
                    "next_hop": r.next_hop,
                    "interface_id": r.interface_id,
                    "admin_distance": r.admin_distance,
                    "metric": r.metric,
                }
                for r in _cap(routes, max_items)
            ]
            doc["routes"] = r_payload
            doc["meta"]["counts"]["routes"] = len(routes)

        if "mac_tables" in want:
            # Group MacAddressEntry by BridgeDomain
            bds = s.exec(select(BridgeDomain)).all()
            macs = s.exec(select(MacAddressEntry)).all()
            by_bd: dict[int, list[dict[str, Any]]] = {}
            for m in macs:
                by_bd.setdefault(m.bridge_domain_id, []).append(
                    {
                        "id": m.id,
                        "mac": m.mac_address,
                        "interface_id": m.interface_id,
                        "type": (m.type.value if hasattr(m.type, "value") else str(m.type)),
                    }
                )
            bd_payload = [
                {
                    "bridge_domain_id": bd.id,
                    "device_id": bd.device_id,
                    "name": bd.name,
                    "entries": _cap(by_bd.get(bd.id, []), max_items),
                }
                for bd in _cap(bds, max_items)
            ]
            doc["mac_tables"] = bd_payload
            doc["meta"]["counts"]["mac_tables"] = len(bds)

    # Metrics V2 snapshot (no DB session required)
    if "metrics_v2" in want:
        snap = get_v2_snapshot()
        # Pass through as-is; enrich with counts and expose deltas if present
        doc["metrics_v2"] = snap
        if isinstance(snap, dict):
            doc["meta"]["tick"] = snap.get("lastTick")

    # Optical snapshot (best-effort)
    if "optical" in want:
        try:
            init_db()
            with get_session() as s2:
                onts = s2.exec(
                    select(Device).where(
                        (Device.type == DeviceType.ONT) | (Device.type == DeviceType.BUSINESS_ONT)
                    )
                ).all()
                ont_entries: list[dict[str, Any]] = []
                for ont in _cap(onts, max_items):
                    path = resolve_optical_path(ont.id)
                    ont_entries.append(
                        {
                            "id": ont.id,
                            "device_type": (
                                ont.type.value if hasattr(ont.type, "value") else str(ont.type)
                            ),
                            "received_dbm": getattr(ont, "signal_power_dbm", None),
                            "margin_db": getattr(ont, "signal_margin_db", None),
                            "signal_status": (
                                ont.signal_status.value
                                if getattr(ont, "signal_status", None)
                                and hasattr(ont.signal_status, "value")
                                else (
                                    str(ont.signal_status)
                                    if getattr(ont, "signal_status", None)
                                    else None
                                )
                            ),
                            "path": (
                                None
                                if not path
                                else {
                                    "olt_id": path.olt_id,
                                    "total_attenuation_db": float(path.total_attenuation_db),
                                    "segments": [
                                        {
                                            "src": seg.src,
                                            "dst": seg.dst,
                                            "link_id": seg.link_id,
                                            "attenuation_db": float(seg.attenuation_db),
                                        }
                                        for seg in path.segments
                                    ],
                                }
                            ),
                        }
                    )
            doc["optical"] = {"onts": ont_entries}
            doc["meta"]["counts"]["optical"] = len(ont_entries)
        except Exception:
            doc["optical"] = {"present": False}

    return doc
