"""Isolated L3 status-recompute micro-benchmark (reusable).

Measures has_upstream_l3_or_anchor() over N leaf devices in ONE session — the exact
path the L3-graph cache (Batch 10) and router-chain cache (Batch 11) optimize. Use it
to get clean before/after numbers on any future status/L3 perf change (run on two
branches and compare). NOT a pytest test (no test_ prefix) — run it directly.

SAFETY: forces its own throwaway sqlite DB and reset_db()s it. It refuses to run
against anything but a sqlite URL, so it can never touch a real Postgres topology.

Run (Git Bash):
    export PYTHONPATH=.
    DATABASE_URL="sqlite:///bench_l3.db" BENCH_N=200 .venv-audit/Scripts/python.exe \
        backend/tests/perf/bench_l3_recompute.py
    rm -f bench_l3.db   # cleanup the throwaway DB

Reference (2026-07-04, N=200): main/Batch-10 ~24600ms -> Batch-11 ~290ms (~85x).
"""
import os
import time

assert os.getenv("DATABASE_URL", "").startswith("sqlite:"), (
    "refuse to run without a throwaway sqlite DATABASE_URL (this calls reset_db())"
)

from sqlmodel import Session  # noqa: E402

from backend.db import engine, init_db, reset_db  # noqa: E402
from backend.models import (  # noqa: E402
    Device,
    DeviceType,
    Interface,
    InterfaceAddress,
    Link,
    Neighbor,
    Route,
    Status,
    VRF,
)
from backend.services.dependency_resolver import has_upstream_l3_or_anchor  # noqa: E402
from backend.services.event_store_runtime import projection_write_context  # noqa: E402
from backend.services.pathfinding import PATHFINDING_STORE  # noqa: E402

N = int(os.getenv("BENCH_N", "200"))


def _mk_device(s, did, dtype):
    s.add(Device(id=did, name=did, type=dtype, status=Status.UP, provisioned=True))


def _mk_link(s, a, b):
    a_if, b_if = f"{a}-if0", f"{b}-if0"
    if s.get(Interface, a_if) is None:
        s.add(Interface(id=a_if, device_id=a, name="if0"))
    if s.get(Interface, b_if) is None:
        s.add(Interface(id=b_if, device_id=b, name="if0"))
    s.add(Link(id=f"{a}__{b}", a_interface_id=a_if, b_interface_id=b_if, status=Status.UP))


reset_db()
init_db()

cpe_ids = []
with projection_write_context(), Session(engine) as s:
    _mk_device(s, "core", DeviceType.BACKBONE_GATEWAY)
    _mk_device(s, "edge", DeviceType.EDGE_ROUTER)
    _mk_link(s, "edge", "core")
    for i in range(N):
        cid = f"cpe{i}"
        _mk_device(s, cid, DeviceType.AON_CPE)
        _mk_link(s, cid, "edge")
        cpe_ids.append(cid)
    # Real routed path so trace_l3_path_to_anchor does actual hop work: edge -> core(anchor)
    vrf = VRF(name="benchvrf")
    s.add(vrf)
    s.flush()
    s.get(Device, "core").vrf_id = vrf.id
    s.get(Device, "edge").vrf_id = vrf.id
    s.add(InterfaceAddress(interface_id="core-if0", ip="10.10.0.1", prefix_len=30, vrf_id=vrf.id))
    s.add(InterfaceAddress(interface_id="edge-if0", ip="10.10.0.2", prefix_len=30, vrf_id=vrf.id))
    s.add(Neighbor(interface_id="edge-if0", ip_address="10.10.0.1", mac_address="00:11:22:33:44:66"))
    s.add(Route(id=1, vrf_id=vrf.id, prefix="0.0.0.0/0", interface_id="edge-if0",
                next_hop="10.10.0.1", admin_distance=1, metric=1))
    s.commit()

PATHFINDING_STORE.bump_version()

with Session(engine) as s3:
    devs = [s3.get(Device, cid) for cid in cpe_ids]  # pre-fetch (untimed)
    t0 = time.perf_counter()
    ok = sum(1 for d in devs if has_upstream_l3_or_anchor(s3, d).ok)
    dt = time.perf_counter() - t0

print(f"RESULT N={N} ok={ok}/{N} total={dt * 1000:.1f}ms per_leaf={dt * 1000 / N:.3f}ms")
