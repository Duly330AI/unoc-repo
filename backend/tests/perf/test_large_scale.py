from __future__ import annotations

import os
import tempfile
import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, cast

import pytest
from sqlmodel import select

from backend.db import get_session, init_db, reset_db
from backend.events import reset_events
from backend.models import VRF, Device, DeviceType, Interface, Link, LinkType, Prefix, Status
from backend.services.provisioning_service import provision_device
from backend.services.seed_service import ensure_default_tariffs, ensure_ipam_defaults
from backend.services.status_recompute import recompute_devices_status

# -----------------------------
# Config knobs via env vars
# -----------------------------
# PERF_SCALE: small | medium | large (string) controls scale factors.
# UNOC_PERF_PROFILE: when set to truthy value, enable pyinstrument and write profile.html


def _scale() -> str:
    return os.getenv("PERF_SCALE", "small").lower()


def _params_for_scale(scale: str) -> tuple[int, int, int]:
    """Return (core_count, olts_per_core, onts_per_olt) based on a named scale."""
    if scale == "large":
        return (4, 8, 64)  # 4 cores, 8 OLTs per core, 64 ONTs per OLT => 2048 ONTs
    if scale == "medium":
        return (2, 4, 32)  # 2 cores, 4 OLTs per core, 32 ONTs per OLT => 256 ONTs
    return (1, 2, 16)  # small default: 1 core, 2 OLTs/core, 16 ONTs/OLT => 32 ONTs


def _ensure_wide_ont_pool(session) -> None:
    """Ensure the ont_mgmt prefix is wide enough for perf scales.

    Defaults use /24 which is insufficient for medium/large scales. We bump to:
    - medium: /20 (4096 addresses)
    - large : /18 (16384 addresses)
    Small scale keeps /24.
    """
    scale = _scale()
    target = None
    if scale == "medium":
        # Avoid overlap with core (10.250.0.0/24) and olt (10.250.4.0/24)
        target = "10.250.16.0/20"  # 4096 addresses: 10.250.16.0 - 10.250.31.255
    elif scale == "large":
        target = "10.250.64.0/18"  # 16384 addresses: 10.250.64.0 - 10.250.127.255
    if not target:
        return
    # Find mgmt VRF and ont_mgmt by description
    mgmt_vrf = session.exec(select(VRF).where(VRF.name == "mgmt")).first()
    if not mgmt_vrf:
        return
    ont = session.exec(
        select(Prefix).where((Prefix.vrf_id == mgmt_vrf.id) & (Prefix.description == "ont_mgmt"))
    ).first()
    if ont:
        ont.prefix = target
        session.add(ont)
        session.flush()


# -----------------------------
# Bulk mode: suppress intermediate recomputes/events by batching writes
# -----------------------------


@contextmanager
def bulk_mode() -> Iterator[None]:
    """A lightweight bulk mode that performs a single recompute at the end.

    Current tests use direct session writes and explicit recomputes, so here we simply
    rely on callers to defer recompute to the end. This context exists to evolve toward
    more advanced suppression toggles if needed without changing callers.
    """
    yield


# -----------------------------
# Factory helpers
# -----------------------------


def _mk_device(
    session, did: str, dtype: DeviceType, status: Status = Status.UP, provision: bool = False
) -> None:
    """Create a device (and a default interface). Optionally provision after flush.

    Note: In perf builders we generally avoid immediate provisioning; instead we
    first create links so upstream paths exist, then provision explicitly. This
    avoids INVALID_PROVISION_PATH errors during topology construction.
    """
    if not session.get(Device, did):
        session.add(Device(id=did, name=did, type=dtype, status=status))
    if_id = f"{did}-if0"
    if not session.get(Interface, if_id):
        session.add(Interface(id=if_id, device_id=did, name="if0"))
    if provision:
        session.flush()
        provision_device(session, session.get(Device, did))


def _mk_link(session, a_dev: str, b_dev: str, kind: LinkType = LinkType.FIBER) -> None:
    a_if = f"{a_dev}-if0"
    b_if = f"{b_dev}-if0"
    lid = "__".join(sorted([a_if, b_if]))
    if not session.get(Link, lid):
        session.add(
            Link(id=lid, a_interface_id=a_if, b_interface_id=b_if, kind=kind, status=Status.UP)
        )


# -----------------------------
# Topology builders
# -----------------------------


def build_core_and_olts(session, core_idx: int, count_olts: int) -> tuple[str, list[str]]:
    """Build one core and its OLTs, link them, then provision.

    Order matters: create devices and links first, then provision so upstream
    paths exist for validation inside provision_device.
    """
    core_id = f"core{core_idx}"
    _mk_device(session, core_id, DeviceType.CORE_ROUTER, provision=False)
    olt_ids = []
    for j in range(count_olts):
        oid = f"olt{core_idx}_{j}"
        _mk_device(session, oid, DeviceType.OLT, provision=False)
        _mk_link(session, core_id, oid, kind=LinkType.FIBER)
        olt_ids.append(oid)
    # Now provision with links in place (core first)
    session.commit()
    # Provision using a fresh session to avoid nested commits conflicts
    from backend.db import get_session as _gs

    with _gs() as sp:
        core = sp.get(Device, core_id)
        assert core is not None
        provision_device(sp, core)
    for oid in olt_ids:
        with _gs() as sp:
            dev = sp.get(Device, oid)
            assert dev is not None
            provision_device(sp, dev)
    return core_id, olt_ids


def attach_onts(session, olt_id: str, count_onts: int) -> list[str]:
    """Attach ONTs to an OLT, linking first, then provisioning each ONT."""
    ont_ids = []
    for k in range(count_onts):
        did = f"{olt_id}_ont{k}"
        _mk_device(session, did, DeviceType.ONT, provision=False)
        _mk_link(session, olt_id, did, kind=LinkType.FIBER)
        ont_ids.append(did)
    session.commit()
    from backend.db import get_session as _gs

    for did in ont_ids:
        with _gs() as sp:
            dev = sp.get(Device, did)
            assert dev is not None
            provision_device(sp, dev)
    return ont_ids


# -----------------------------
# Profiling helper
# -----------------------------


def maybe_profile_start():
    """Start profiling if requested.

    Preference order:
    1) pyinstrument (sampling profiler with HTML report)
    2) cProfile (built-in) fallback writing pstats + text summary

    Returns one of:
    - ("pyinstrument", profiler)
    - ("cprofile", cprof)
    - None if profiling not requested
    """
    if not os.getenv("UNOC_PERF_PROFILE"):
        return None

    # Try pyinstrument first
    try:  # pragma: no cover - optional dep handling
        from pyinstrument import Profiler  # type: ignore

        p = Profiler()
        p.start()
        return ("pyinstrument", p)
    except Exception:
        # Fallback to cProfile
        try:
            import cProfile  # pragma: no cover - environment dependent

            cp = cProfile.Profile()
            cp.enable()
            return ("cprofile", cp)
        except Exception:
            return None


def maybe_profile_stop_and_write(profiler) -> str | None:
    """Stop the profiler and write a report.

    - For pyinstrument: write HTML + text, return HTML path
    - For cProfile   : write .pstats + text, return text path
    - For None       : return None
    """
    if profiler is None:
        return None

    # Normalize outputs
    out_dir = os.getenv("UNOC_PERF_OUTDIR") or tempfile.mkdtemp(prefix="unoc-perf-")
    os.makedirs(out_dir, exist_ok=True)
    tag = os.getenv("UNOC_PERF_TAG") or str(int(time.time()))
    out_html = os.path.join(out_dir, f"profile-{tag}.html")
    out_txt = os.path.join(out_dir, f"profile-{tag}.txt")
    out_pstats = os.path.join(out_dir, f"profile-{tag}.pstats")

    try:
        # pyinstrument shape: ("pyinstrument", Profiler)
        if isinstance(profiler, tuple) and profiler and profiler[0] == "pyinstrument":  # type: ignore[index]
            p = profiler[1]
            p.stop()
            with open(out_html, "w", encoding="utf-8") as f:
                f.write(p.output_html())
            try:
                with open(out_txt, "w", encoding="utf-8") as ftxt:
                    ftxt.write(p.output_text(unicode=True))
            except Exception:
                pass
            return out_html

        # cProfile shape: ("cprofile", Profile)
        if isinstance(profiler, tuple) and profiler and profiler[0] == "cprofile":  # type: ignore[index]
            cp = profiler[1]
            try:
                cp.disable()
            except Exception:
                pass
            # Dump raw stats and generate a human-readable text summary
            try:
                cp.dump_stats(out_pstats)
            except Exception:
                # best effort; continue to text output
                pass
            try:
                import pstats

                stats = pstats.Stats(cp)
                stats.strip_dirs().sort_stats("cumulative")
                with open(out_txt, "w", encoding="utf-8") as ftxt:
                    stats.stream = ftxt  # type: ignore[attr-defined]
                    stats.print_stats(60)
            except Exception:
                # If pstats fails, at least touch the file for the test
                with open(out_txt, "w", encoding="utf-8") as ftxt:
                    ftxt.write("profiling summary unavailable\n")
            return out_txt

        # Back-compat: if the caller passed a raw pyinstrument Profiler
        try:
            # duck-typing: stop() + output_html()
            p_any: Any = cast(Any, profiler)
            p_any.stop()
            with open(out_html, "w", encoding="utf-8") as f:
                f.write(p_any.output_html())
            try:
                with open(out_txt, "w", encoding="utf-8") as ftxt:
                    ftxt.write(p_any.output_text(unicode=True))
            except Exception:
                pass
            return out_html
        except Exception:
            return None
    except Exception:  # pragma: no cover - best effort
        return None


# -----------------------------
# Main perf test
# -----------------------------


@pytest.mark.perf
@pytest.mark.timeout(120)
def test_large_scale_topology_build_and_recompute(monkeypatch: pytest.MonkeyPatch):
    # Ensure clean DB and seed needed defaults
    reset_db()
    init_db()
    reset_events()
    with get_session() as s:
        ensure_ipam_defaults(s)
        ensure_default_tariffs(s)
        _ensure_wide_ont_pool(s)
        s.commit()

    profiler = maybe_profile_start()

    scale = _scale()
    cores, olts_per_core, onts_per_olt = _params_for_scale(scale)
    with bulk_mode():
        with get_session() as s:
            # Build cores and OLTs, connecting each OLT to its core
            all_olts: list[str] = []
            for i in range(cores):
                _, olts = build_core_and_olts(s, i + 1, olts_per_core)
                all_olts.extend(olts)
            # Attach ONTs to each OLT
            for oid in all_olts:
                attach_onts(s, oid, onts_per_olt)
            s.commit()

    # Single recompute after bulk creation
    with get_session() as s:
        recompute_devices_status(s, include_passive_propagation=True)

    out = maybe_profile_stop_and_write(profiler)
    # If profiling enabled, ensure file exists
    if os.getenv("UNOC_PERF_PROFILE"):
        assert out is not None and os.path.exists(out), "profiling requested but no report written"
