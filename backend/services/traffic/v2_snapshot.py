from __future__ import annotations


def build_snapshot_maps(
    device_changes: list[dict], link_changes: list[dict]
) -> tuple[dict[str, dict], dict[str, dict]]:
    dev_map: dict[str, dict] = {}
    for item in device_changes:
        u = float(item.get("utilization", 0.0))
        dev_map[item["id"]] = {
            "bps": float(item.get("bps", 0.0)),
            "utilization": 1e9 if u == float("inf") else u,
            "version": 0,
            "upstream_bps": float(item.get("upstream_bps", 0.0)),
            "downstream_bps": float(item.get("downstream_bps", 0.0)),
        }
    link_map: dict[str, dict] = {}
    for item in link_changes:
        u = float(item.get("utilization", 0.0))
        link_map[item["id"]] = {
            "bps": float(item.get("bps", 0.0)),
            "utilization": 1e9 if u == float("inf") else u,
            "version": 0,
        }
    return dev_map, link_map
