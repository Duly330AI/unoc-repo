"""Debug-only layered device state model.

The model keeps physical, dataplane, network, and service values separate so
diagnostics do not blend capacity, MAC learning, routing, and subscribers.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from sqlmodel import Session, select

from backend.models import Device, Interface, InterfaceAddress, Link, MacAddressEntry, Neighbor, Route
from backend.services.subscriber_model import PASSIVE_TYPES, subscriber_parameters


def _type_name(value: Any) -> str:
    raw = getattr(value, "value", value)
    return str(raw or "").upper()


def _value(value: Any) -> Any:
    return getattr(value, "value", value)


def resolve_layered_device_state(
    session: Session, subscriber_model: dict[str, Any], optical_state: dict[str, Any] | None = None
) -> dict[str, Any]:
    devices = list(session.exec(select(Device)).all())
    interfaces = list(session.exec(select(Interface)).all())
    links = list(session.exec(select(Link)).all())
    mac_entries = list(session.exec(select(MacAddressEntry)).all())
    addresses = list(session.exec(select(InterfaceAddress)).all())
    routes = list(session.exec(select(Route)).all())
    neighbors = list(session.exec(select(Neighbor)).all())

    ifaces_by_device: dict[str, list[Interface]] = defaultdict(list)
    for iface in interfaces:
        ifaces_by_device[iface.device_id].append(iface)

    link_count_by_if: Counter[str] = Counter()
    for link in links:
        link_count_by_if[link.a_interface_id] += 1
        link_count_by_if[link.b_interface_id] += 1

    mac_by_if: dict[str, list[MacAddressEntry]] = defaultdict(list)
    for entry in mac_entries:
        mac_by_if[entry.interface_id].append(entry)

    addr_by_if: dict[str, list[InterfaceAddress]] = defaultdict(list)
    for address in addresses:
        addr_by_if[address.interface_id].append(address)

    route_by_if: dict[str, list[Route]] = defaultdict(list)
    for route in routes:
        if route.interface_id:
            route_by_if[route.interface_id].append(route)

    neighbor_by_if: dict[str, list[Neighbor]] = defaultdict(list)
    for neighbor in neighbors:
        neighbor_by_if[neighbor.interface_id].append(neighbor)

    states: dict[str, dict[str, Any]] = {}
    for device in sorted(devices, key=lambda item: item.id):
        dev_type = _type_name(device.type)
        dev_ifaces = sorted(ifaces_by_device.get(device.id, []), key=lambda item: (item.name, item.id))
        iface_ids = {iface.id for iface in dev_ifaces}
        service = subscriber_parameters(subscriber_model, device.id)
        service_applies = dev_type in {"OLT", "AON_SWITCH", "ONT", "BUSINESS_ONT", "AON_CPE"}
        optical_device = (optical_state or {}).get("devices", {}).get(device.id, {})

        states[device.id] = {
            "physical": {
                "layer": "L1_PHYSICAL",
                "device_type": dev_type,
                "port_count": len(dev_ifaces),
                "link_count": sum(link_count_by_if[iface.id] for iface in dev_ifaces),
                "insertion_loss_db": getattr(device, "insertion_loss_db", None),
                "optical_physics": {
                    "modeled": bool(optical_device)
                    and not bool(optical_device.get("excluded_from_optical_physics")),
                    "excluded": bool(optical_device.get("excluded_from_optical_physics", False)),
                    "measured_loss_db": optical_device.get("measured_loss_db"),
                    "port_states": optical_device.get("port_states", {}),
                },
                "ports": [
                    {
                        "id": iface.id,
                        "name": iface.name,
                        "port_role": _value(iface.port_role),
                        "capacity_mbps": iface.capacity,
                        "admin_status": _value(iface.admin_status),
                        "physical_link_count": int(link_count_by_if[iface.id]),
                    }
                    for iface in dev_ifaces
                ],
            },
            "dataplane": {
                "layer": "L2_DATAPLANE",
                "modeled": dev_type not in PASSIVE_TYPES,
                "mac_entries": [
                    {
                        "mac_address": entry.mac_address,
                        "interface_id": entry.interface_id,
                        "type": _value(entry.type),
                    }
                    for iface_id in iface_ids
                    for entry in sorted(mac_by_if.get(iface_id, []), key=lambda item: item.mac_address)
                ],
            },
            "network": {
                "layer": "L3_NETWORK",
                "interface_addresses": [
                    {
                        "interface_id": address.interface_id,
                        "ip": address.ip,
                        "prefix_len": address.prefix_len,
                        "vrf_id": address.vrf_id,
                    }
                    for iface_id in iface_ids
                    for address in sorted(addr_by_if.get(iface_id, []), key=lambda item: item.ip)
                ],
                "routes": [
                    {
                        "interface_id": route.interface_id,
                        "prefix": route.prefix,
                        "next_hop": route.next_hop,
                        "metric": route.metric,
                    }
                    for iface_id in iface_ids
                    for route in sorted(route_by_if.get(iface_id, []), key=lambda item: item.prefix)
                ],
                "neighbors": [
                    {
                        "interface_id": neighbor.interface_id,
                        "ip_address": neighbor.ip_address,
                        "mac_address": neighbor.mac_address,
                    }
                    for iface_id in iface_ids
                    for neighbor in sorted(neighbor_by_if.get(iface_id, []), key=lambda item: item.ip_address)
                ],
            },
            "service": {
                "layer": "L4_SERVICE",
                "modeled": service_applies,
                "provisioned": bool(getattr(device, "provisioned", False)),
                "subscribers": int(service.get("total") or 0) if service_applies else None,
                "subscriber_domain": service.get("domain") if service_applies else None,
                "subscriber_ids": list(service.get("subscriber_ids") or []) if service_applies else [],
                "source": "subscriber_model" if service_applies else "not_applicable",
            },
        }

    return {
        "contract": {
            "L1_PHYSICAL": "ports, uplinks, physical capacity, physical loss",
            "L2_DATAPLANE": "MAC addresses and learned switching entries",
            "L3_NETWORK": "IP addresses, neighbors, and routes",
            "L4_SERVICE": "subscriber identity, provisioning, and service attachment",
            "rules": [
                "physical ports do not store subscriber counts",
                "MAC learning does not affect subscriber counts",
                "IP paths do not affect port capacity",
                "subscriber counts come only from L4_SERVICE",
            ],
        },
        "devices": states,
    }