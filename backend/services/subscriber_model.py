"""Canonical subscriber aggregation over the current topology graph."""

from __future__ import annotations

from collections import Counter, defaultdict, deque
from typing import Any

from sqlmodel import Session, select

from backend.models import Device, DeviceType, Interface, Link, PortRole

ONT_TYPES = {"ONT", "BUSINESS_ONT"}
CPE_TYPES = {"AON_CPE"}
PASSIVE_TYPES = {"ODF", "NVT", "SPLITTER", "HOP"}


def _type_name(value: Any) -> str:
    raw = getattr(value, "value", value)
    return str(raw or "").upper()


def _port_role(value: Any) -> str:
    raw = getattr(value, "value", value)
    return str(raw or "").upper()


def _is_provisioned(device: Device) -> bool:
    return bool(getattr(device, "provisioned", False))


def resolve_subscriber_model(session: Session) -> dict[str, Any]:
    devices = list(session.exec(select(Device)).all())
    interfaces = list(session.exec(select(Interface)).all())
    links = list(session.exec(select(Link)).all())

    devices_by_id = {device.id: device for device in devices}
    interfaces_by_id = {iface.id: iface for iface in interfaces}
    interfaces_by_device: dict[str, list[Interface]] = defaultdict(list)
    for iface in sorted(interfaces, key=lambda item: (item.device_id, item.name, item.id)):
        interfaces_by_device[iface.device_id].append(iface)

    link_neighbors: dict[str, set[str]] = defaultdict(set)
    for link in links:
        if link.a_interface_id and link.b_interface_id:
            link_neighbors[link.a_interface_id].add(link.b_interface_id)
            link_neighbors[link.b_interface_id].add(link.a_interface_id)

    raw_by_type = Counter(_type_name(device.type) for device in devices)
    provisioned_by_type = Counter(
        _type_name(device.type) for device in devices if _is_provisioned(device)
    )

    per_node: dict[str, dict[str, Any]] = {
        device.id: {
            "id": device.id,
            "type": _type_name(device.type),
            "subscribers": 0,
            "subscriber_ids": [],
            "subscriber_domain": None,
        }
        for device in devices
    }
    pon_occupancy: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    aon_access_occupancy: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    decisions: list[dict[str, Any]] = []

    def sibling_ids(iface: Interface) -> list[str]:
        device = devices_by_id.get(iface.device_id)
        if not device:
            return []
        dev_type = _type_name(device.type)
        if dev_type not in PASSIVE_TYPES and dev_type not in ONT_TYPES and dev_type not in CPE_TYPES:
            return []
        return [other.id for other in interfaces_by_device.get(iface.device_id, []) if other.id != iface.id]

    def trace_anchor(start_device: Device, domain: str) -> tuple[str, str | None, str] | None:
        queue: deque[str] = deque(iface.id for iface in interfaces_by_device.get(start_device.id, []))
        visited: set[str] = set(queue)
        while queue:
            iface_id = queue.popleft()
            iface = interfaces_by_id.get(iface_id)
            if not iface:
                continue
            device = devices_by_id.get(iface.device_id)
            if not device:
                continue
            dev_type = _type_name(device.type)
            if domain == "OLT" and dev_type == "OLT" and _port_role(iface.port_role) == "PON":
                return device.id, iface.id, "first_reachable_olt_pon"
            if domain == "AON" and dev_type == "AON_SWITCH":
                return device.id, iface.id, "first_reachable_aon_switch"

            next_ids = sorted(link_neighbors.get(iface_id, set())) + sibling_ids(iface)
            for next_id in next_ids:
                if next_id not in visited:
                    visited.add(next_id)
                    queue.append(next_id)
        return None

    for device in sorted(devices, key=lambda item: item.id):
        dev_type = _type_name(device.type)
        if dev_type not in ONT_TYPES and dev_type not in CPE_TYPES:
            continue
        if not _is_provisioned(device):
            decisions.append(
                {
                    "subscriber_id": device.id,
                    "subscriber_type": dev_type,
                    "counted": False,
                    "reason": "not_provisioned",
                }
            )
            continue

        leaf_domain = "OLT" if dev_type in ONT_TYPES else "AON"
        leaf_node = per_node[device.id]
        leaf_node["subscribers"] = 1
        leaf_node["subscriber_ids"] = [device.id]
        leaf_node["subscriber_domain"] = leaf_domain

        anchor = trace_anchor(device, leaf_domain)
        if not anchor:
            decisions.append(
                {
                    "subscriber_id": device.id,
                    "subscriber_type": dev_type,
                    "counted": False,
                    "domain": leaf_domain,
                    "reason": "no_reachable_anchor",
                }
            )
            continue

        anchor_id, interface_id, reason = anchor
        anchor_node = per_node[anchor_id]
        if device.id not in anchor_node["subscriber_ids"]:
            anchor_node["subscriber_ids"].append(device.id)
            anchor_node["subscriber_ids"].sort()
            anchor_node["subscribers"] = len(anchor_node["subscriber_ids"])
            anchor_node["subscriber_domain"] = leaf_domain

        if leaf_domain == "OLT" and interface_id:
            pon_occupancy[anchor_id][interface_id] += 1
        if leaf_domain == "AON" and interface_id:
            aon_access_occupancy[anchor_id][interface_id] += 1

        decisions.append(
            {
                "subscriber_id": device.id,
                "subscriber_type": dev_type,
                "counted": True,
                "domain": leaf_domain,
                "anchor_device_id": anchor_id,
                "anchor_interface_id": interface_id,
                "reason": reason,
            }
        )

    olt_total = sum(
        node["subscribers"]
        for node in per_node.values()
        if node["subscriber_domain"] == "OLT" and node["type"] == "OLT"
    )
    aon_total = sum(
        node["subscribers"]
        for node in per_node.values()
        if node["subscriber_domain"] == "AON" and node["type"] == "AON_SWITCH"
    )

    return {
        "raw_device_counts": {
            "by_type": dict(sorted(raw_by_type.items())),
            "provisioned_by_type": dict(sorted(provisioned_by_type.items())),
        },
        "global": {
            "subscriber": {
                "total": int(provisioned_by_type.get("ONT", 0))
                + int(provisioned_by_type.get("BUSINESS_ONT", 0))
                + int(provisioned_by_type.get("AON_CPE", 0)),
                "olt_domain": int(provisioned_by_type.get("ONT", 0))
                + int(provisioned_by_type.get("BUSINESS_ONT", 0)),
                "aon_domain": int(provisioned_by_type.get("AON_CPE", 0)),
                "resolved_olt_domain": olt_total,
                "resolved_aon_domain": aon_total,
            }
        },
        "resolved_subscribers": per_node,
        "pon_occupancy": {
            device_id: dict(sorted(ports.items())) for device_id, ports in sorted(pon_occupancy.items())
        },
        "aon_access_occupancy": {
            device_id: dict(sorted(ports.items()))
            for device_id, ports in sorted(aon_access_occupancy.items())
        },
        "mapping_decisions": decisions,
    }


def subscriber_parameters(model: dict[str, Any], device_id: str) -> dict[str, Any]:
    node = model.get("resolved_subscribers", {}).get(device_id, {})
    return {
        "total": int(node.get("subscribers") or 0),
        "domain": node.get("subscriber_domain"),
        "subscriber_ids": list(node.get("subscriber_ids") or []),
    }


def pon_occupancy_for(model: dict[str, Any], device_id: str) -> dict[str, int]:
    return {str(k): int(v) for k, v in model.get("pon_occupancy", {}).get(device_id, {}).items()}


def aon_access_occupancy_for(model: dict[str, Any], device_id: str) -> dict[str, int]:
    return {
        str(k): int(v) for k, v in model.get("aon_access_occupancy", {}).get(device_id, {}).items()
    }