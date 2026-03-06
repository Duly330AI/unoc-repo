from __future__ import annotations

import backend.events as events


def handle_device_congestion(
    prev: set[str],
    device_changes: list[dict],
    detect_threshold: float,
    clear_threshold: float,
    tick: int,
) -> set[str]:
    current: set[str] = set()
    for item in device_changes:
        did = item["id"]
        bps = float(item["bps"])
        util = float(item.get("utilization", 0.0))
        capacity_bps = (bps / util) if util > 0 else bps
        if did in prev:
            if util >= clear_threshold:
                current.add(did)
        else:
            if util >= detect_threshold:
                current.add(did)
                overload_pct = (util - 1.0) * 100.0 if util != float("inf") else float("inf")
                events.publish(
                    events.Event(
                        type="device.congestion.detected",
                        payload={
                            "id": did,
                            "aggregated_bps": bps,
                            "capacity_bps": capacity_bps,
                            "overload_percentage": overload_pct,
                            "tick": tick,
                        },
                    )
                )
    for did in list(prev):
        if did not in current:
            item = next((x for x in device_changes if x["id"] == did), None)
            if item is not None:
                bps = float(item["bps"])  # below capacity now
                util = float(item.get("utilization", 0.0))
                capacity_bps = bps / util if util > 0 else bps
            else:
                capacity_bps = 0.0
                bps = 0.0
            events.publish(
                events.Event(
                    type="device.congestion.cleared",
                    payload={
                        "id": did,
                        "aggregated_bps": bps,
                        "capacity_bps": capacity_bps,
                        "tick": tick,
                    },
                )
            )
    return current


def handle_link_congestion(
    prev: set[str],
    link_changes: list[dict],
    detect_threshold: float,
    clear_threshold: float,
    tick: int,
) -> set[str]:
    current: set[str] = set()
    for item in link_changes:
        lid = item["id"]
        bps = float(item["bps"])
        util = float(item.get("utilization", 0.0))
        capacity_bps = bps / util if util > 0 else bps
        if lid in prev:
            if util >= clear_threshold:
                current.add(lid)
        else:
            if util >= detect_threshold:
                current.add(lid)
                overload_pct = (util - 1.0) * 100.0 if util != float("inf") else float("inf")
                events.publish(
                    events.Event(
                        type="link.congestion.detected",
                        payload={
                            "id": lid,
                            "aggregated_bps": bps,
                            "capacity_bps": capacity_bps,
                            "overload_percentage": overload_pct,
                            "tick": tick,
                        },
                    )
                )
    for lid in list(prev):
        if lid not in current:
            item = next((x for x in link_changes if x["id"] == lid), None)
            if item is not None:
                bps = float(item["bps"])  # below capacity now
                util = float(item.get("utilization", 0.0))
                capacity_bps = bps / util if util > 0 else bps
            else:
                capacity_bps = 0.0
                bps = 0.0
            events.publish(
                events.Event(
                    type="link.congestion.cleared",
                    payload={
                        "id": lid,
                        "aggregated_bps": bps,
                        "capacity_bps": capacity_bps,
                        "tick": tick,
                    },
                )
            )
    return current
