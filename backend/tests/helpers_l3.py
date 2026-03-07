from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy.exc import InterfaceError
from sqlmodel import select

from backend.db import get_session, init_db
from backend.models import (
    VRF,
    AdminStatus,
    Device,
    Interface,
    InterfaceAddress,
    Link,
    Neighbor,
    Route,
)

# ruff: noqa: I001


def ensure_vrf(name: str = "mgmt") -> int:
    """Create or get a VRF by name and return its id."""
    init_db()
    with get_session() as s:
        v = s.exec(select(VRF).where(VRF.name == name)).first()
        if v:
            return int(v.id)  # type: ignore[arg-type]
        v = VRF(name=name)
        s.add(v)
        s.commit()
        s.refresh(v)
        return int(v.id)  # type: ignore[arg-type]


def assign_device_vrf(device_id: str, vrf_id: int) -> None:
    init_db()
    with get_session() as s:
        d = s.get(Device, device_id)
        if not d:
            raise RuntimeError("DEVICE_NOT_FOUND")
        d.vrf_id = vrf_id
        s.add(d)
        s.commit()


def up_ifaces(*interface_ids: str) -> None:
    init_db()
    with get_session() as s:
        for iid in interface_ids:
            i = s.get(Interface, iid)
            if not i:
                raise RuntimeError("INTERFACE_NOT_FOUND")
            i.admin_status = AdminStatus.UP
            s.add(i)
        s.commit()


def add_interface_address(
    interface_id: str, ip: str, prefix_len: int, vrf_id: int | None = None
) -> int:
    init_db()
    with get_session() as s:
        ia = InterfaceAddress(
            interface_id=interface_id, ip=ip, prefix_len=prefix_len, vrf_id=vrf_id
        )
        s.add(ia)
        s.commit()
        s.refresh(ia)
        return int(ia.id)  # type: ignore[arg-type]


def add_neighbor(interface_id: str, ip: str, mac: str) -> int:
    init_db()
    with get_session() as s:
        nb = Neighbor(interface_id=interface_id, ip_address=ip, mac_address=mac)
        s.add(nb)
        s.commit()
        s.refresh(nb)
        return int(nb.id)  # type: ignore[arg-type]


def add_default_route(
    vrf_id: int, next_hop: str, interface_id: str, admin_distance: int = 1, metric: int = 0
) -> int:
    init_db()
    with get_session() as s:
        r = Route(
            vrf_id=vrf_id,
            prefix="0.0.0.0/0",
            next_hop=next_hop,
            interface_id=interface_id,
            admin_distance=admin_distance,
            metric=metric,
        )
        s.add(r)
        s.commit()
        s.refresh(r)
        return int(r.id)  # type: ignore[arg-type]


def add_ptp_addresses(
    a_iface: str,
    b_iface: str,
    cidr: str,
    vrf_id: int | None = None,
    *,
    bitmask: int | None = None,
) -> tuple[str, str]:
    """Assign two host IPs from a /31 or /30 CIDR to the given interfaces.

    Returns the (a_ip, b_ip). If bitmask is provided, overrides cidr mask parsing.
    """
    import ipaddress

    net = ipaddress.ip_network(cidr)
    hosts = list(net.hosts())
    if len(hosts) < 2:
        raise RuntimeError("CIDR_HAS_INSUFFICIENT_HOSTS")
    a_ip = str(hosts[0])
    b_ip = str(hosts[1])
    mask = bitmask if bitmask is not None else net.prefixlen
    add_interface_address(a_iface, a_ip, mask, vrf_id)
    add_interface_address(b_iface, b_ip, mask, vrf_id)
    return a_ip, b_ip


@contextmanager
def l3_pair(
    a_device: str,
    b_device: str,
    a_iface: str,
    b_iface: str,
    vrf_name: str = "mgmt",
    ptp_cidr: str = "172.16.0.0/31",
    a_mac: str = "aa:bb:cc:00:00:01",
    b_mac: str = "aa:bb:cc:00:00:02",
):
    """Context manager that sets up a simple L3 adjacency and tears it down implicitly.

    - Ensures VRF exists and assigns to both devices.
    - Assigns /31 addresses to a_iface/b_iface.
    - Adds Neighbor bindings in both directions.
    - Adds default route for a_device pointing to b_iface IP (egress a_iface).
    """
    vrf_id = ensure_vrf(vrf_name)
    assign_device_vrf(a_device, vrf_id)
    assign_device_vrf(b_device, vrf_id)
    # Ensure interfaces exist and are administratively up; create if missing
    init_db()
    with get_session() as s:
        # Defensive: ensure we start from a clean transactional state in case a prior helper
        # invocation left the connection in a failed transaction (e.g., due to a uniqueness
        # violation that was caught higher up). SQLite can raise 'InterfaceError: bad parameter'
        # sporadically if a failed transaction isn't rolled back before the next execute.
        try:  # short, silent rollback attempt
            s.rollback()
        except Exception:
            # If rollback itself fails, continue; subsequent operations will surface real errors.
            pass

        # Helper to ensure (id, device_id, name) tuple exists; tolerate races/previous creation
        def _ensure_interface(iface_id: str, device_id: str) -> None:
            try:
                existing = s.get(Interface, iface_id)
            except InterfaceError:
                # Transient driver state (e.g., leftover failed tx on same connection); rollback & retry once
                try:
                    s.rollback()
                except Exception:
                    pass
                existing = s.get(Interface, iface_id)
            if existing:
                existing.admin_status = AdminStatus.UP
                s.add(existing)
                return
            name_part = iface_id.split("-", 1)[-1]
            try:
                s.add(
                    Interface(
                        id=iface_id,
                        device_id=device_id,
                        name=name_part,
                        admin_status=AdminStatus.UP,
                    )
                )
                s.flush()
            except Exception:  # noqa: BLE001 - convert uniqueness race to fetch
                s.rollback()
                # Re-fetch by id; if still missing, re-raise
                refetched = s.get(Interface, iface_id)
                if not refetched:
                    raise
                refetched.admin_status = AdminStatus.UP
                s.add(refetched)

        _ensure_interface(a_iface, a_device)
        _ensure_interface(b_iface, b_device)
        # Ensure a link exists between the two interfaces
        existing = s.exec(
            select(Link).where(
                ((Link.a_interface_id == a_iface) & (Link.b_interface_id == b_iface))
                | ((Link.a_interface_id == b_iface) & (Link.b_interface_id == a_iface))
            )
        ).first()
        if not existing:
            link_id = f"lnk-{a_iface}--{b_iface}"
            s.add(Link(id=link_id, a_interface_id=a_iface, b_interface_id=b_iface))
        s.commit()
    a_ip, b_ip = add_ptp_addresses(a_iface, b_iface, ptp_cidr, vrf_id)
    add_neighbor(a_iface, b_ip, b_mac)
    add_neighbor(b_iface, a_ip, a_mac)
    add_default_route(vrf_id, next_hop=b_ip, interface_id=a_iface)
    try:
        yield (vrf_id, a_ip, b_ip)
    finally:
        # Cleanup is handled by test DB resets between tests.
        pass
