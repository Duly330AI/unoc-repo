from __future__ import annotations

from types import SimpleNamespace

from backend.db import get_session, init_db
from backend.models import Device, DeviceType, Status
from backend.services.status_service import evaluate_device_status, recompute_dirty


def _mk_dev(session, dev_id: str, t: DeviceType = DeviceType.EDGE_ROUTER) -> Device:
    d = session.get(Device, dev_id)
    if d is None:
        d = Device(id=dev_id, name=dev_id, type=t)
        session.add(d)
        session.commit()
    return d


def test_recompute_dirty_locality_transitions():
    init_db()
    with get_session() as s:
        # Core anchor (ALWAYS_ONLINE)
        _mk_dev(s, "core", DeviceType.BACKBONE_GATEWAY)
        # Two active, unprovisioned routers (baseline DOWN by rule)
        a = _mk_dev(s, "a", DeviceType.EDGE_ROUTER)
        m = _mk_dev(s, "m", DeviceType.EDGE_ROUTER)

        # Baseline map (before change): both expected DOWN
        baseline = {
            "a": evaluate_device_status(a),
            "m": evaluate_device_status(m),
        }
        assert baseline["a"] == Status.DOWN and baseline["m"] == Status.DOWN

        # Apply change: force both UP via admin override
        a.admin_override_status = Status.UP
        m.admin_override_status = Status.UP
        s.add(a)
        s.add(m)
        s.commit()

        # Incremental recompute on dirty devices only
        cfg = SimpleNamespace(enable_incremental=True, baseline_status=baseline)
        dirty = {"devices": ["m", "a"]}  # intentionally unsorted
        transitions = recompute_dirty(s, dirty, cfg=cfg)

        # Only changed devices, and both flipped DOWN -> UP
        as_set = {(t[0], t[1], t[2]) for t in transitions}
        assert as_set == {("a", "Status.DOWN", "Status.UP"), ("m", "Status.DOWN", "Status.UP")}


def test_recompute_dirty_deterministic_results_repeat():
    init_db()
    with get_session() as s:
        _mk_dev(s, "core", DeviceType.BACKBONE_GATEWAY)
        x = _mk_dev(s, "x", DeviceType.EDGE_ROUTER)
        y = _mk_dev(s, "y", DeviceType.EDGE_ROUTER)

        baseline = {"x": evaluate_device_status(x), "y": evaluate_device_status(y)}
        assert baseline["x"] == Status.DOWN and baseline["y"] == Status.DOWN

        x.admin_override_status = Status.UP
        y.admin_override_status = Status.UP
        s.add(x)
        s.add(y)
        s.commit()

        cfg = SimpleNamespace(enable_incremental=True, baseline_status=baseline)
        dirty = {"devices": ["y", "x"]}
        r1 = recompute_dirty(s, dirty, cfg=cfg)
        # Repeat the same call; since we provide the same baseline, results should be identical
        r2 = recompute_dirty(s, dirty, cfg=cfg)
        assert r1 == r2


def test_recompute_dirty_parity_with_full_recompute():
    init_db()
    with get_session() as s:
        _mk_dev(s, "core", DeviceType.BACKBONE_GATEWAY)
        p = _mk_dev(s, "p", DeviceType.EDGE_ROUTER)
        q = _mk_dev(s, "q", DeviceType.EDGE_ROUTER)

        baseline = {"p": evaluate_device_status(p), "q": evaluate_device_status(q)}
        assert all(v == Status.DOWN for v in baseline.values())

        # Change both
        p.admin_override_status = Status.UP
        q.admin_override_status = Status.UP
        s.add(p)
        s.add(q)
        s.commit()

        dirty = {"devices": ["p", "q"]}
        cfg_inc = SimpleNamespace(enable_incremental=True, baseline_status=baseline)
        cfg_full = SimpleNamespace(enable_incremental=False, baseline_status=baseline)

        inc = recompute_dirty(s, dirty, cfg=cfg_inc)
        full = recompute_dirty(s, dirty, cfg=cfg_full)

        assert sorted(inc) == sorted(full)
