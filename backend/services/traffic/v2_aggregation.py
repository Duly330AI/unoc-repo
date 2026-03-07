from __future__ import annotations

from collections.abc import Iterable

from sqlmodel import Session, select

from backend.models import Device, Interface, InterfaceRole, Link
from backend.services.catalog_effective import (
    get_effective_device_capacity_mbps,
    get_effective_interface_capacity_mbps,
)


def compute_device_changes(
    s: Session,
    dev_rows: Iterable[Device],
    per_device_totals: dict[str, float],
    per_device_down_totals: dict[str, float],
) -> list[dict]:
    dev_list = list(dev_rows)
    cap_map: dict[str, int | None] = {
        d.id: get_effective_device_capacity_mbps(s, d) for d in dev_list
    }
    device_changes: list[dict] = []
    for did, bps in per_device_totals.items():
        # Re-read current device and allow metrics unless administratively forced DOWN.
        # This permits infrastructure devices (e.g., CORE/EDGE) to carry traffic even
        # when they are DEGRADED due to upstream anchors being unavailable.
        try:
            d_now = s.get(Device, did)
            if d_now is None:
                allow_metrics = True
            else:
                aov = getattr(d_now, "admin_override_status", None)
                aov_val = None
                if aov is not None:
                    try:
                        aov_val = aov.value  # type: ignore[attr-defined]
                    except Exception:
                        aov_val = None
                allow_metrics = not ((str(aov) == "DOWN") or (aov_val == "DOWN"))
        except Exception:
            allow_metrics = True
        eff_bps = float(bps) if allow_metrics else 0.0
        cap_mbps = cap_map.get(did)
        if cap_mbps is None or cap_mbps <= 0:
            util = 0.0 if eff_bps <= 0 else float("inf")
        else:
            util = eff_bps / (cap_mbps * 1_000_000.0)
        device_changes.append(
            {
                "id": did,
                "bps": eff_bps,
                "utilization": util,
                "upstream_bps": float(per_device_totals.get(did, 0.0)) if allow_metrics else 0.0,
                "downstream_bps": (
                    float(per_device_down_totals.get(did, 0.0)) if allow_metrics else 0.0
                ),
            }
        )
    return device_changes


def compute_link_changes(
    s: Session,
    per_link_totals: dict[str, float],
    per_link_down_totals: dict[str, float],
) -> tuple[list[dict], dict[str, dict[str, dict]]]:
    link_changes: list[dict] = []
    ports_map: dict[str, dict[str, dict]] = {}
    if not per_link_totals:
        return link_changes, ports_map

    link_rows = s.exec(select(Link)).all()
    if_rows = s.exec(select(Interface)).all()
    if_cap: dict[str, int | None] = {
        i.id: get_effective_interface_capacity_mbps(s, i) for i in if_rows
    }
    endpoints: dict[str, tuple[str, str]] = {
        row.id: (row.a_interface_id, row.b_interface_id) for row in link_rows
    }

    DEFAULT_LINK_CAP_MBPS = 1000.0
    per_iface_bps: dict[str, float] = {}
    for lid, bps in per_link_totals.items():
        a_if, b_if = endpoints.get(lid, ("", ""))
        cap_a = if_cap.get(a_if)
        cap_b = if_cap.get(b_if)
        caps = [c for c in [cap_a, cap_b] if c is not None and c > 0]
        cap_mbps = float(min(caps)) if caps else DEFAULT_LINK_CAP_MBPS
        util = 0.0 if cap_mbps <= 0 and bps <= 0 else (bps / (cap_mbps * 1_000_000.0))
        link_changes.append({"id": lid, "bps": bps, "utilization": util})

        total_bps = float(bps) + float(per_link_down_totals.get(lid, 0.0))
        if a_if:
            per_iface_bps[a_if] = per_iface_bps.get(a_if, 0.0) + total_bps
        if b_if:
            per_iface_bps[b_if] = per_iface_bps.get(b_if, 0.0) + total_bps

    if per_iface_bps:
        if_rows_all = if_rows
        dev_by_iface: dict[str, str] = {i.id: i.device_id for i in if_rows_all}
        role_by_iface: dict[str, InterfaceRole | None] = {i.id: i.role for i in if_rows_all}
        if_cap_all: dict[str, int | None] = if_cap
        # Iterate interfaces in priority order: P2P_UPLINK first for stable finite utilization
        items_sorted = sorted(
            per_iface_bps.items(),
            key=lambda kv: 0 if role_by_iface.get(kv[0]) == InterfaceRole.P2P_UPLINK else 1,
        )
        for iface_id, ibps in items_sorted:
            dev_id = dev_by_iface.get(iface_id)
            if not dev_id:
                continue
            cap_mbps = if_cap_all.get(iface_id)
            if cap_mbps is None or cap_mbps <= 0:
                u = 0.0 if ibps <= 0 else float("inf")
            else:
                u = ibps / (cap_mbps * 1_000_000.0)
            dmap = ports_map.setdefault(dev_id, {})
            dmap[iface_id] = {
                "bps": float(ibps),
                "utilization": 1e9 if u == float("inf") else float(u),
                "version": 0,
            }

    return link_changes, ports_map
