from ipaddress import ip_network

from fastapi.testclient import TestClient
from sqlmodel import select

from backend.db import get_session
from backend.main import app
from backend.models import VRF, InterfaceAddress, Prefix
from backend.services.seed_service import ensure_ipam_defaults


def test_ipam_pools_list_with_stats():
    client = TestClient(app)
    # Ensure mgmt VRF and prefixes exist, then attach two InterfaceAddresses to core_mgmt
    with get_session() as s:
        ensure_ipam_defaults(s)
        mgmt = s.exec(select(VRF).where(VRF.name == "mgmt")).first()
        assert mgmt is not None
        core = s.exec(
            select(Prefix).where((Prefix.vrf_id == mgmt.id) & (Prefix.description == "core_mgmt"))
        ).first()
        assert core is not None
        # For deterministic capacity, shrink to a /29
        core.prefix = "10.0.0.0/29"
        s.add(core)
        s.commit()
        net = ip_network(core.prefix)
        hosts = list(net.hosts())
        # add two addresses bound to this Prefix
        for i in range(2):
            s.add(
                InterfaceAddress(
                    interface_id=f"t-if-{i}",
                    ip=str(hosts[i]),
                    prefix_len=net.prefixlen,
                    prefix_id=core.id,
                    vrf_id=mgmt.id,
                )
            )
        s.commit()

    r = client.get("/api/ipam/pools")
    assert r.status_code == 200
    data = r.json()
    # find the core_mgmt row
    core_row = next((row for row in data if row["pool_key"] == "core_mgmt"), None)
    assert core_row is not None
    assert core_row["cidr"] == "10.0.0.0/29"
    assert core_row["capacity"] == 6  # /29 has 6 hosts
    assert core_row["allocated_count"] == 2
    assert 0.0 < core_row["utilization"] < 1.0


def test_ipam_pools_list_empty():
    client = TestClient(app)
    r = client.get("/api/ipam/pools")
    assert r.status_code == 200
    # In a clean DB with no mgmt VRF/prefixes, endpoint yields []
    assert r.json() == []
