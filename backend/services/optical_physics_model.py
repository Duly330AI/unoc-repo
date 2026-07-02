"""Debug-only L1 optical physics model.

This module models optical power propagation separately from L2/L3/L4 state.
It does not mutate device status, subscriber mappings, routing, or UI state.
"""

from __future__ import annotations

import math
from collections import defaultdict, deque
from typing import Any

from sqlmodel import Session, select

from backend.constants import FIBER_TYPES
from backend.models import Device, DeviceType, Interface, Link, LinkType, PhysicalMedium
from backend.services.catalog_effective import get_effective_sensitivity_dbm, get_effective_tx_power_dbm

DEFAULT_CONNECTOR_LOSS_DB = 0.2
DEFAULT_FIBER_ATTENUATION_DB_PER_KM = 0.35
OPTICAL_SOURCE_TYPES = {"OLT"}
OPTICAL_TERMINAL_TYPES = {"ONT", "BUSINESS_ONT"}
OPTICAL_PASSIVE_TYPES = {"SPLITTER", "ODF", "NVT", "HOP"}
OPTICAL_EXCLUDED_TYPES = {"AON_SWITCH"}


def _type_name(value: Any) -> str:
    raw = getattr(value, "value", value)
    return str(raw or "").upper()


def _link_type(value: Any) -> str:
    raw = getattr(value, "value", value)
    return str(raw or "").upper()


def _port_state(
    interface_id: str,
    input_power_dbm: float | None,
    output_power_dbm: float | None,
    total_loss_db: float,
    sensitivity_threshold_dbm: float | None,
) -> dict[str, Any]:
    link_budget_ok = (
        output_power_dbm is not None
        and sensitivity_threshold_dbm is not None
        and output_power_dbm >= sensitivity_threshold_dbm
    )
    if sensitivity_threshold_dbm is None:
        link_budget_ok = True
    status = "UP" if link_budget_ok else "DOWN (OPTICAL LOSS)"
    return {
        "interface_id": interface_id,
        "optical_input_power_dbm": input_power_dbm,
        "optical_output_power_dbm": output_power_dbm,
        "total_loss_db": round(total_loss_db, 4),
        "sensitivity_threshold_dbm": sensitivity_threshold_dbm,
        "link_budget_ok": bool(link_budget_ok),
        "status": status,
    }


def _medium_loss(session: Session, link: Link) -> tuple[str | None, float]:
    if link.physical_medium_id is None:
        return None, DEFAULT_FIBER_ATTENUATION_DB_PER_KM
    medium = session.get(PhysicalMedium, link.physical_medium_id)
    if medium and medium.code in FIBER_TYPES:
        return medium.code, float(FIBER_TYPES[medium.code].attenuation_db_per_km)
    return getattr(medium, "code", None), DEFAULT_FIBER_ATTENUATION_DB_PER_KM


def _splitter_loss_db(splitter: Device, output_count: int) -> float:
    if splitter.insertion_loss_db is not None:
        return float(splitter.insertion_loss_db)
    if output_count <= 1:
        return 0.0
    return 10.0 * math.log10(float(output_count))


def _find_path(
    source_id: str,
    target_id: str,
    devices_by_id: dict[str, Device],
    ifaces_by_device: dict[str, list[Interface]],
    iface_device_by_id: dict[str, str],
    links_by_if: dict[str, list[Link]],
) -> list[tuple[str, str, str | None]] | None:
    queue: deque[tuple[str, list[tuple[str, str, str | None]]]] = deque(
        (iface.id, [(iface.device_id, iface.id, None)]) for iface in ifaces_by_device.get(source_id, [])
    )
    visited = {iface.id for iface in ifaces_by_device.get(source_id, [])}
    while queue:
        iface_id, path = queue.popleft()
        current_device_id = path[-1][0]
        if current_device_id == target_id:
            return path

        for link in sorted(links_by_if.get(iface_id, []), key=lambda item: item.id):
            peer_if_id = link.b_interface_id if link.a_interface_id == iface_id else link.a_interface_id
            if not peer_if_id or peer_if_id in visited:
                continue
            peer_device_id = iface_device_by_id.get(peer_if_id)
            if not peer_device_id:
                continue
            visited.add(peer_if_id)
            queue.append((peer_if_id, path + [(peer_device_id, peer_if_id, link.id)]))

        current_device = devices_by_id.get(current_device_id)
        current_device_type = _type_name(current_device.type) if current_device else ""
        can_cross_device = current_device_id == source_id or current_device_type in OPTICAL_PASSIVE_TYPES
        if can_cross_device:
            for sibling in ifaces_by_device.get(current_device_id, []):
                if sibling.id not in visited:
                    visited.add(sibling.id)
                    queue.append((sibling.id, path + [(sibling.device_id, sibling.id, None)]))

    return None


def resolve_optical_physics_state(session: Session) -> dict[str, Any]:
    devices = list(session.exec(select(Device)).all())
    interfaces = list(session.exec(select(Interface)).all())
    links = list(session.exec(select(Link)).all())

    devices_by_id = {device.id: device for device in devices}
    ifaces_by_device: dict[str, list[Interface]] = defaultdict(list)
    iface_by_id = {iface.id: iface for iface in interfaces}
    iface_device_by_id = {iface.id: iface.device_id for iface in interfaces}
    for iface in sorted(interfaces, key=lambda item: (item.device_id, item.name, item.id)):
        ifaces_by_device[iface.device_id].append(iface)

    links_by_id = {link.id: link for link in links}
    links_by_if: dict[str, list[Link]] = defaultdict(list)
    for link in links:
        if _link_type(link.kind) == LinkType.FIBER.value:
            links_by_if[link.a_interface_id].append(link)
            links_by_if[link.b_interface_id].append(link)

    source_devices = [device for device in devices if _type_name(device.type) in OPTICAL_SOURCE_TYPES]
    terminal_devices = [
        device
        for device in devices
        if _type_name(device.type) in OPTICAL_TERMINAL_TYPES and bool(device.provisioned)
    ]

    device_loss: dict[str, dict[str, Any]] = {
        device.id: {
            "device_id": device.id,
            "device_type": _type_name(device.type),
            "excluded_from_optical_physics": _type_name(device.type) in OPTICAL_EXCLUDED_TYPES,
            "measured_loss_db": 0.0,
            "port_states": {},
        }
        for device in devices
    }
    paths: dict[str, Any] = {}

    for terminal in sorted(terminal_devices, key=lambda item: item.id):
        candidates: list[tuple[float, str, list[tuple[str, str, str | None]]]] = []
        for source in source_devices:
            path = _find_path(source.id, terminal.id, devices_by_id, ifaces_by_device, iface_device_by_id, links_by_if)
            if path:
                candidates.append((float(len(path)), source.id, path))
        if not candidates:
            paths[terminal.id] = {
                "target_device_id": terminal.id,
                "target_device_type": _type_name(terminal.type),
                "resolved": False,
                "reason": "no_optical_source_path",
            }
            continue

        _, source_id, path = sorted(candidates, key=lambda item: (item[0], item[1]))[0]
        source = devices_by_id[source_id]
        tx_power_dbm = get_effective_tx_power_dbm(session, source)
        sensitivity_dbm = get_effective_sensitivity_dbm(session, terminal)
        current_power_dbm = tx_power_dbm
        total_loss_db = 0.0
        hops: list[dict[str, Any]] = []
        previous_device_id = source_id

        for index, (device_id, iface_id, link_id) in enumerate(path):
            device = devices_by_id[device_id]
            device_type = _type_name(device.type)
            input_power_dbm = current_power_dbm
            link_loss_db = 0.0
            connector_loss_db = 0.0
            insertion_loss_db = 0.0
            splitter_loss_db = 0.0
            attenuation_db_per_km = None
            length_km = None
            medium_code = None

            if link_id:
                link = links_by_id[link_id]
                medium_code, attenuation_db_per_km = _medium_loss(session, link)
                length_km = float(link.length_km or 0.0)
                link_loss_db = length_km * float(attenuation_db_per_km)
                connector_loss_db = DEFAULT_CONNECTOR_LOSS_DB

            if index not in {0, len(path) - 1} and device_type in OPTICAL_PASSIVE_TYPES:
                if device_type == "SPLITTER" and link_id is None:
                    output_count = sum(
                        1 for iface in ifaces_by_device.get(device_id, []) if iface.name.lower().startswith("out")
                    )
                    splitter_loss_db = _splitter_loss_db(device, output_count)
                elif device_type in {"NVT"} and device.insertion_loss_db is not None:
                    insertion_loss_db = float(device.insertion_loss_db)

            hop_loss_db = link_loss_db + connector_loss_db + insertion_loss_db + splitter_loss_db
            total_loss_db += hop_loss_db
            current_power_dbm = tx_power_dbm - total_loss_db

            if device_type in OPTICAL_PASSIVE_TYPES or device_type in OPTICAL_TERMINAL_TYPES:
                device_loss[device_id]["measured_loss_db"] = round(
                    max(float(device_loss[device_id]["measured_loss_db"]), hop_loss_db), 4
                )

            threshold = sensitivity_dbm if device_id == terminal.id else None
            device_loss[device_id]["port_states"][iface_id] = _port_state(
                iface_id, input_power_dbm, current_power_dbm, total_loss_db, threshold
            )

            hops.append(
                {
                    "from_device_id": previous_device_id if link_id else device_id,
                    "to_device_id": device_id,
                    "interface_id": iface_id,
                    "link_id": link_id,
                    "physical_medium_code": medium_code,
                    "length_km": length_km,
                    "attenuation_db_per_km": attenuation_db_per_km,
                    "insertion_loss_db": round(insertion_loss_db, 4),
                    "connector_loss_db": round(connector_loss_db, 4),
                    "splitter_loss_db": round(splitter_loss_db, 4),
                    "fiber_attenuation_loss_db": round(link_loss_db, 4),
                    "total_optical_loss_db": round(hop_loss_db, 4),
                    "cumulative_loss_db": round(total_loss_db, 4),
                    "optical_input_power_dbm": round(input_power_dbm, 4),
                    "optical_output_power_dbm": round(current_power_dbm, 4),
                }
            )
            previous_device_id = device_id

        rx_power_dbm = current_power_dbm
        paths[terminal.id] = {
            "source_device_id": source_id,
            "target_device_id": terminal.id,
            "target_device_type": _type_name(terminal.type),
            "resolved": True,
            "tx_power_dbm": tx_power_dbm,
            "rx_power_dbm": round(rx_power_dbm, 4),
            "sensitivity_threshold_dbm": sensitivity_dbm,
            "total_loss_db": round(total_loss_db, 4),
            "link_budget_ok": rx_power_dbm >= sensitivity_dbm,
            "status": "UP" if rx_power_dbm >= sensitivity_dbm else "DOWN (OPTICAL LOSS)",
            "hops": hops,
        }

    return {
        "layer": "L1_PHYSICAL",
        "rules": {
            "aon_switch": "excluded: AON switching is treated as electrical dataplane, not optical physics",
            "subscriber_logic": "unchanged: no L4 subscriber fields are used or modified",
            "ip_routing": "unchanged: no L3 path or route data is used",
        },
        "defaults": {
            "connector_loss_db": DEFAULT_CONNECTOR_LOSS_DB,
            "fallback_attenuation_db_per_km": DEFAULT_FIBER_ATTENUATION_DB_PER_KM,
        },
        "devices": device_loss,
        "paths": paths,
        "signal_degradation_map": {
            target_id: {
                "source_device_id": path.get("source_device_id"),
                "rx_power_dbm": path.get("rx_power_dbm"),
                "total_loss_db": path.get("total_loss_db"),
                "link_budget_ok": path.get("link_budget_ok"),
                "status": path.get("status"),
            }
            for target_id, path in paths.items()
        },
    }


__all__ = ["resolve_optical_physics_state"]