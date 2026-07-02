"""Unified count semantics for physical, provisioned, and effective counts."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from sqlmodel import Session, select

from backend.models import Device, Interface, Link
from backend.services.subscriber_model import (
    CPE_TYPES,
    ONT_TYPES,
    SUBSCRIBER_SOURCE,
    resolve_subscriber_model,
)

COUNT_SOURCE = "DEVICE_COUNT_MODEL"


def _type_name(value: Any) -> str:
    raw = getattr(value, "value", value)
    return str(raw or "").upper()


def _is_provisioned(device: Device) -> bool:
    return bool(getattr(device, "provisioned", False))


def _build_interface_maps(
    interfaces: list[Interface], links: list[Link]
) -> tuple[dict[str, Interface], dict[str, list[Link]]]:
    ifaces = {iface.id: iface for iface in interfaces}
    links_by_if: dict[str, list[Link]] = defaultdict(list)
    for link in links:
        links_by_if[link.a_interface_id].append(link)
        links_by_if[link.b_interface_id].append(link)
    return ifaces, links_by_if


def _direct_cpe_anchor(
    device: Device, devices_by_id: dict[str, Device], ifaces: dict[str, Interface], links_by_if: dict[str, list[Link]]
) -> tuple[str, str] | None:
    for iface in ifaces.values():
        if iface.device_id != device.id:
            continue
        for link in links_by_if.get(iface.id, []):
            peer_id = link.b_interface_id if link.a_interface_id == iface.id else link.a_interface_id
            peer = ifaces.get(peer_id)
            peer_device = devices_by_id.get(peer.device_id) if peer else None
            if peer and peer_device and _type_name(peer_device.type) == "AON_SWITCH":
                return peer.device_id, peer.id
    return None


def _trace_olt_anchor(
    device: Device,
    devices_by_id: dict[str, Device],
    ifaces_by_device: dict[str, list[Interface]],
    ifaces_by_id: dict[str, Interface],
    links_by_if: dict[str, list[Link]],
) -> tuple[str, str] | None:
    queue = [iface.id for iface in ifaces_by_device.get(device.id, [])]
    visited = set(queue)
    while queue:
        iface_id = queue.pop(0)
        iface = ifaces_by_id.get(iface_id)
        if not iface:
            continue
        current = devices_by_id.get(iface.device_id)
        if not current:
            continue
        current_type = _type_name(current.type)
        if current_type == "OLT" and str(getattr(iface.port_role, "value", iface.port_role) or "").upper() == "PON":
            return current.id, iface.id
        can_cross = current_type in {"ODF", "NVT", "SPLITTER", "HOP"} | ONT_TYPES
        for link in links_by_if.get(iface_id, []):
            peer_id = link.b_interface_id if link.a_interface_id == iface_id else link.a_interface_id
            if peer_id and peer_id not in visited:
                visited.add(peer_id)
                queue.append(peer_id)
        if can_cross:
            for sibling in ifaces_by_device.get(current.id, []):
                if sibling.id not in visited:
                    visited.add(sibling.id)
                    queue.append(sibling.id)
    return None


def build_count_semantics(session: Session) -> dict[str, Any]:
    devices = list(session.exec(select(Device)).all())
    interfaces = list(session.exec(select(Interface)).all())
    links = list(session.exec(select(Link)).all())
    subscriber_model = resolve_subscriber_model(session)

    devices_by_id = {device.id: device for device in devices}
    ifaces_by_device: dict[str, list[Interface]] = defaultdict(list)
    for iface in interfaces:
        ifaces_by_device[iface.device_id].append(iface)
    ifaces_by_id, links_by_if = _build_interface_maps(interfaces, links)

    raw_by_type = Counter(_type_name(device.type) for device in devices)
    provisioned_by_type = Counter(_type_name(device.type) for device in devices if _is_provisioned(device))
    counted_decisions = {
        decision.get("subscriber_id"): decision
        for decision in subscriber_model.get("mapping_decisions", [])
        if decision.get("subscriber_id")
    }
    physical_olt: dict[str, set[str]] = defaultdict(set)
    physical_pon: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    physical_aon: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    provisioned_aon: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))

    for device in devices:
        dev_type = _type_name(device.type)
        if dev_type in ONT_TYPES:
            anchor = _trace_olt_anchor(device, devices_by_id, ifaces_by_device, ifaces_by_id, links_by_if)
            if anchor:
                olt_id, pon_id = anchor
                physical_olt[olt_id].add(device.id)
                physical_pon[olt_id][pon_id].add(device.id)
        if dev_type in CPE_TYPES:
            anchor = _direct_cpe_anchor(device, devices_by_id, ifaces_by_id, links_by_if)
            if anchor:
                aon_id, access_id = anchor
                physical_aon[aon_id][access_id].add(device.id)
                if _is_provisioned(device):
                    provisioned_aon[aon_id][access_id].add(device.id)

    count_model: dict[str, dict[str, Any]] = {}
    mismatches: list[dict[str, Any]] = []
    orphaned_devices: list[dict[str, Any]] = []

    for device in sorted(devices, key=lambda item: item.id):
        dev_type = _type_name(device.type)
        node = subscriber_model.get("resolved_subscribers", {}).get(device.id, {})
        physical_count = 1 if dev_type in ONT_TYPES or dev_type in CPE_TYPES else len(ifaces_by_device.get(device.id, []))
        provisioned_count = 1 if (dev_type in ONT_TYPES or dev_type in CPE_TYPES) and _is_provisioned(device) else 0
        effective_count = int(node.get("subscribers") or 0)
        if dev_type == "OLT":
            physical_count = len(physical_olt.get(device.id, set()))
            provisioned_count = sum(subscriber_model.get("pon_occupancy", {}).get(device.id, {}).values())
            effective_count = int(node.get("subscribers") or 0)
        elif dev_type == "AON_SWITCH":
            physical_count = sum(len(cpes) for cpes in physical_aon.get(device.id, {}).values())
            provisioned_count = sum(len(cpes) for cpes in provisioned_aon.get(device.id, {}).values())
            effective_count = int(node.get("subscribers") or 0)
        if dev_type in ONT_TYPES or dev_type in CPE_TYPES:
            decision = counted_decisions.get(device.id)
            effective_count = 1 if decision and decision.get("counted") is True else 0
        elif dev_type not in {"OLT", "AON_SWITCH"}:
            effective_count = 0

        delta = physical_count - provisioned_count
        entry = {
            "device_id": device.id,
            "device_type": dev_type,
            "physical_count": physical_count,
            "provisioned_count": provisioned_count,
            "effective_count": effective_count,
            "mismatch_delta": delta,
            "count_source": COUNT_SOURCE,
            "effective_source": SUBSCRIBER_SOURCE if dev_type in {"OLT", "AON_SWITCH", *ONT_TYPES, *CPE_TYPES} else "not_applicable",
            "warnings": [],
        }
        if physical_count != provisioned_count:
            warning = {
                "code": "PHYSICAL_PROVISIONING_MISMATCH",
                "device_id": device.id,
                "device_type": dev_type,
                "physical_count": physical_count,
                "provisioned_count": provisioned_count,
                "mismatch_delta": delta,
                "severity": 60,
            }
            entry["warnings"].append(warning)
            mismatches.append(warning)

        decision = counted_decisions.get(device.id)
        if dev_type in ONT_TYPES | CPE_TYPES and _is_provisioned(device) and (not decision or decision.get("counted") is not True):
            orphaned_devices.append(
                {
                    "device_id": device.id,
                    "device_type": dev_type,
                    "reason": decision.get("reason") if decision else "no_l4_mapping_decision",
                    "mapped_port_id": decision.get("anchor_interface_id") if decision else None,
                }
            )

        count_model[device.id] = entry

    for device_id, ports in subscriber_model.get("pon_ports", {}).items():
        for port_id, state in ports.items():
            physical_count = len(physical_pon.get(device_id, {}).get(port_id, set()))
            provisioned_count = int(state.get("provisioned_onts_count") or 0)
            count_model[port_id] = {
                "device_id": port_id,
                "device_type": "PON",
                "parent_device_id": device_id,
                "physical_count": physical_count,
                "provisioned_count": provisioned_count,
                "effective_count": provisioned_count,
                "max_capacity": state.get("max_capacity"),
                "utilization": state.get("utilization"),
                "mismatch_delta": physical_count - provisioned_count,
                "count_source": COUNT_SOURCE,
                "effective_source": SUBSCRIBER_SOURCE,
                "warnings": [],
            }

    oversubscription = [
        decision
        for decision in subscriber_model.get("mapping_decisions", [])
        if decision.get("reason") == "aon_access_port_oversubscribed_1_to_1"
    ]

    return {
        "model": "DeviceCountModel",
        "semantics": {
            "physical_count": "all existing hardware elements",
            "provisioned_count": "elements mapped or eligible in L4_PROVISIONING_GRAPH",
            "effective_count": "authoritative value consumers should display",
        },
        "raw_device_counts": {
            "physical_by_type": dict(sorted(raw_by_type.items())),
            "provisioned_by_type": dict(sorted(provisioned_by_type.items())),
        },
        "global": {
            "physical_count": sum(item["physical_count"] for item in count_model.values() if item.get("device_type") in ONT_TYPES | CPE_TYPES),
            "provisioned_count": sum(item["provisioned_count"] for item in count_model.values() if item.get("device_type") in ONT_TYPES | CPE_TYPES),
            "effective_count": subscriber_model.get("global", {}).get("subscriber", {}).get("total", 0),
        },
        "devices": count_model,
        "mismatches": mismatches,
        "oversubscription_mapping": oversubscription,
        "orphaned_devices": orphaned_devices,
    }


def count_semantics_for(model: dict[str, Any], device_id: str) -> dict[str, Any]:
    return dict(model.get("devices", {}).get(device_id, {}))


__all__ = ["COUNT_SOURCE", "build_count_semantics", "count_semantics_for"]