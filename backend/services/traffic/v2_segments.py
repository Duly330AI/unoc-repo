"""Traffic V2 segments aggregation and shaping helpers.

Extracted from v2_engine to keep the engine module small and readable.
This module computes per PON-segment demand/capacity, applies shaping,
tracks congestion with hysteresis, and emits segment events.
"""

from __future__ import annotations

import backend.events as events
from backend.models import DeviceType, Interface, PortRole
from backend.services.optical_path_resolver import resolve_optical_path


def _pon_caps(engine, olt_dev_id: str, iface: Interface) -> tuple[float, float, int | None]:
    """Return (down_bps, up_bps, max_subscribers) for the given OLT PON interface.

    Uses model PortProfiles from engine caches and follows the same rules as v2_engine.
    """
    # Defaults: GPON 2.5G/1.25G
    down = 2.5e9
    up = 1.25e9
    max_subs: int | None = None
    hw = engine._dev_hw_model_by_id.get(olt_dev_id)
    profs = engine._profiles_by_hw_model.get(hw, []) if hw else []
    pname = (getattr(iface, "profile_name", None) or "").strip()
    # Try exact match by name first
    p = next((pp for pp in profs if (pp.name or "").strip() == pname), None)
    # Fallback: role PON profiles on the model
    if p is None:
        p = next((pp for pp in profs if getattr(pp, "port_role", None) == PortRole.PON), None)
    if p is not None:
        try:
            if p.max_subscribers is not None:
                max_subs = int(p.max_subscribers)
        except Exception:
            max_subs = None
        try:
            sp = float(p.speed_gbps) if p.speed_gbps is not None else None
            media = (p.media or "").lower() if getattr(p, "media", None) else ""
            name_l = (p.name or "").lower()
            if sp is not None:
                if "xgs" in media or "xgs" in name_l:
                    down = sp * 1e9
                    up = sp * 1e9
                elif "xg" in media or "xgpon" in name_l:
                    # XG-PON asymmetric 10G/2.5G when speed advertises downstream
                    down = sp * 1e9
                    up = 2.5e9
                else:
                    # If generic speed provided for PON, assume downstream; keep GPON upstream
                    down = sp * 1e9
        except Exception:
            pass
    return float(down), float(up), max_subs


def compute_segments_map(
    engine,
    per_device_totals: dict[str, float],
    per_device_down_totals: dict[str, float],
    tick: int,
) -> dict:
    """Compute per-segment aggregation and congestion.

    Mutates engine._prev_segment_congested for hysteresis and emits events.
    Returns the segments_map. Any exceptions are expected to be handled by the caller.
    """
    # Ensure caches are ready
    engine._ensure_profiles_cache()

    # Shorthands for caches
    if_by_id = engine._iface_by_id
    neigh_by_if = engine._neigh_by_if
    olt_pon_ifaces = engine._olt_pon_ifaces_by_olt
    dev_types = engine._dev_type_by_id

    segments_map: dict[str, dict] = {}

    # Determine ONTs that generated demand this tick (from per_device totals)
    ont_ids = [
        did
        for did in sorted(per_device_totals.keys())
        if dev_types.get(did) in {DeviceType.ONT, DeviceType.BUSINESS_ONT}
    ]

    # Aggregate per segment
    for ont_id in ont_ids:
        # Resolve optical path with cache per topology version
        r = engine._optical_path_cache.get(ont_id)
        if r is None:
            try:
                r = resolve_optical_path(ont_id)
            except Exception:
                r = None
            # Cache result (including None) to avoid repeated work in the same tick/version
            engine._optical_path_cache[ont_id] = r
        if not r:
            continue
        olt_id = getattr(r, "olt_id", None)
        if not olt_id or olt_id not in olt_pon_ifaces:
            continue
        segs = list(getattr(r, "segments", []) or [])
        # Determine ODF id as neighbor to OLT along the path
        odf_id = None
        for sg in segs:
            try:
                s_src = getattr(sg, "src", None)
                s_dst = getattr(sg, "dst", None)
                if s_src == olt_id and s_dst:
                    odf_id = s_dst
                    break
                if s_dst == olt_id and s_src:
                    odf_id = s_src
                    break
            except Exception:
                continue
        # Fallback: best-effort choose any neighbor device of a PON iface
        if odf_id is None:
            cands: list[str] = []
            for pi in olt_pon_ifaces.get(olt_id, []):
                for nb in sorted(neigh_by_if.get(pi.id, set())):
                    cands.append(nb)
            odf_id = sorted(set(cands))[0] if cands else None
        if odf_id is None:
            continue
        # Determine specific PON interface via neighbor mapping
        pon_if_id = None
        for pi in olt_pon_ifaces.get(olt_id, []):  # already sorted by name in cache
            if odf_id in neigh_by_if.get(pi.id, set()):
                pon_if_id = pi.id
                break
        if pon_if_id is None and olt_pon_ifaces.get(olt_id):
            pon_if_id = olt_pon_ifaces[olt_id][0].id
        if pon_if_id is None:
            continue
        seg_id = f"{pon_if_id}::{odf_id}"
        up_demand = float(per_device_totals.get(ont_id, 0.0))
        down_demand = float(per_device_down_totals.get(ont_id, 0.0))
        entry = segments_map.setdefault(
            seg_id,
            {
                "id": seg_id,
                "olt_id": olt_id,
                "pon_port_id": pon_if_id,
                "odf_id": odf_id,
                "subscribers_count": 0,
                "subscribers_max": None,
                "capacity_down_bps": 0.0,
                "capacity_up_bps": 0.0,
                "demand_down_bps": 0.0,
                "demand_up_bps": 0.0,
                "used_down_bps": 0.0,
                "used_up_bps": 0.0,
                "headroom_down_bps": 0.0,
                "headroom_up_bps": 0.0,
                "congested": False,
            },
        )
        entry["subscribers_count"] += 1
        entry["demand_up_bps"] += up_demand
        entry["demand_down_bps"] += down_demand
        # Ensure capacity populated from chosen PON interface
        if entry["capacity_down_bps"] == 0.0 and entry["capacity_up_bps"] == 0.0:
            pi = if_by_id.get(pon_if_id)
            if pi is not None:
                d_bps, u_bps, max_subs = _pon_caps(engine, olt_id, pi)
                entry["capacity_down_bps"] = d_bps
                entry["capacity_up_bps"] = u_bps
                if max_subs is not None:
                    entry["subscribers_max"] = max_subs

    # Finalize shaping and hysteresis state; emit events
    current_segment_congested: set[str] = set()
    for sid, e in segments_map.items():
        cap_d = max(float(e.get("capacity_down_bps", 0.0)), 0.0)
        cap_u = max(float(e.get("capacity_up_bps", 0.0)), 0.0)
        dem_d = max(float(e.get("demand_down_bps", 0.0)), 0.0)
        dem_u = max(float(e.get("demand_up_bps", 0.0)), 0.0)
        used_d = min(dem_d, cap_d) if cap_d > 0 else dem_d
        used_u = min(dem_u, cap_u) if cap_u > 0 else dem_u
        e["used_down_bps"] = used_d
        e["used_up_bps"] = used_u
        e["headroom_down_bps"] = max(cap_d - used_d, 0.0)
        e["headroom_up_bps"] = max(cap_u - used_u, 0.0)
        util_d = (dem_d / cap_d) if cap_d > 0 else 0.0
        util_u = (dem_u / cap_u) if cap_u > 0 else 0.0
        util = max(util_d, util_u)
        prev = sid in engine._prev_segment_congested
        if prev:
            if util >= engine.segment_clear_threshold:
                current_segment_congested.add(sid)
                e["congested"] = True
            else:
                e["congested"] = False
                # cleared event
                try:
                    events.publish(
                        events.Event(
                            type="segment.congestion.cleared",
                            payload={
                                "id": sid,
                                "olt_id": e.get("olt_id"),
                                "pon_port_id": e.get("pon_port_id"),
                                "odf_id": e.get("odf_id"),
                                "tick": tick,
                            },
                        )
                    )
                except Exception:
                    pass
        else:
            if util >= engine.segment_detect_threshold:
                current_segment_congested.add(sid)
                e["congested"] = True
                # detected event
                try:
                    events.publish(
                        events.Event(
                            type="segment.congestion.detected",
                            payload={
                                "id": sid,
                                "olt_id": e.get("olt_id"),
                                "pon_port_id": e.get("pon_port_id"),
                                "odf_id": e.get("odf_id"),
                                "demand_down_bps": dem_d,
                                "demand_up_bps": dem_u,
                                "capacity_down_bps": cap_d,
                                "capacity_up_bps": cap_u,
                                "tick": tick,
                            },
                        )
                    )
                except Exception:
                    pass
            else:
                e["congested"] = False

    engine._prev_segment_congested = current_segment_congested
    return segments_map
