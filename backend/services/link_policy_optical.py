"""
Optical link policy helpers extracted from links endpoint.

These functions encapsulate ONT placement rules (ODF-anchored passive paths),
Splitter V1 capacity enforcement, OLT PON-role validation, and single-upstream
constraints for ODF/ONT devices.

All functions raise HTTPException via raise_error or directly where appropriate
when a rule is violated; otherwise they return None.
"""

from __future__ import annotations

from sqlmodel import select

from backend.constants import ONT_CLASS, PASSIVE_INLINE
from backend.errors import ErrorCode, raise_error
from backend.models import Device, DeviceType, Interface, Link, PortRole
from backend.services.splitter_service import (
    compute_splitter_usage,
    find_out_interface_reaching,
    out_interface_has_ont,
)


def enforce_ont_placement_rules(
    s,
    a_dev: Device,
    b_dev: Device,
    a_interface_id: str,
    b_interface_id: str,
) -> None:
    """Ensure ONT connects either to an ODF or to a passive inline device that
    resides within an ODF-headed, OLT-anchored path; and enforce Splitter V1
    capacity constraints.

    - If ONT connects to ODF: allowed.
    - If ONT connects to passive inline (NVT/SPLITTER/HOP): require that passive is
      in a path which reaches an ODF that neighbors an OLT.
    - For SPLITTER:
        * One ONT per OUT port (no over-subscription)
        * Total downstream ONTs across OUTs must be < ports_total
    """
    if (a_dev.type not in ONT_CLASS) and (b_dev.type not in ONT_CLASS):
        return

    other = b_dev if a_dev.type in ONT_CLASS else a_dev
    if other.type == DeviceType.ODF:
        return  # allowed
    if other.type not in PASSIVE_INLINE:
        raise_error(
            ErrorCode.LINK_INVALID_UPSTREAM,
            detail_suffix=f"ONT must connect upstream to an ODF or passive, not {other.type.name}",
        )

    # Build adjacency among passives and ODF so we can verify anchoring to an OLT
    links = s.exec(select(Link)).all()

    # cache device types to avoid repeated lookups
    dev_type_cache: dict[str, DeviceType] = {}

    def _dtype(did: str) -> DeviceType | None:
        t = dev_type_cache.get(did)
        if t is not None:
            return t
        d = s.get(Device, did)
        if not d:
            return None
        dev_type_cache[did] = d.type
        return d.type

    adj: dict[str, set[str]] = {}

    def _add_edge(x: str, y: str) -> None:
        adj.setdefault(x, set()).add(y)

    # Track which ODFs have an OLT neighbor
    odf_with_olt: set[str] = set()
    for ln in links:
        try:
            ia = s.get(Interface, ln.a_interface_id)
        except Exception:
            ia = None
        try:
            ib = s.get(Interface, ln.b_interface_id)
        except Exception:
            ib = None
        if not ia or not ib:
            continue
        da, db = ia.device_id, ib.device_id
        ta, tb = _dtype(da), _dtype(db)
        if ta is None or tb is None:
            continue
        if ta in PASSIVE_INLINE and tb in PASSIVE_INLINE:
            _add_edge(da, db)
            _add_edge(db, da)
        if (ta in PASSIVE_INLINE and tb == DeviceType.ODF) or (
            tb in PASSIVE_INLINE and ta == DeviceType.ODF
        ):
            _add_edge(da, db)
            _add_edge(db, da)
        if (ta == DeviceType.ODF and tb == DeviceType.OLT) or (
            tb == DeviceType.ODF and ta == DeviceType.OLT
        ):
            odf_with_olt.add(da if ta == DeviceType.ODF else db)

    # Fast-path: direct neighbor ODF that neighbors an OLT
    anchored_ok = False
    passive_id = other.id
    dev_adj: dict[str, set[str]] = {}
    for ln in links:
        try:
            ia = s.get(Interface, ln.a_interface_id)
            ib = s.get(Interface, ln.b_interface_id)
        except Exception:
            ia = ib = None
        if not ia or not ib:
            continue
        da, db = ia.device_id, ib.device_id
        dev_adj.setdefault(da, set()).add(db)
        dev_adj.setdefault(db, set()).add(da)
    for nb in dev_adj.get(passive_id, set()):
        if _dtype(nb) == DeviceType.ODF:
            if any(_dtype(x) == DeviceType.OLT for x in dev_adj.get(nb, set())):
                anchored_ok = True
                break

    # BFS from passive across passive/ODF adjacency to locate an ODF known to neighbor an OLT
    if not anchored_ok:
        start = other.id
        visited = {start}
        queue: list[str] = [start]
        while queue and not anchored_ok:
            cur = queue.pop(0)
            tcur = _dtype(cur)
            if tcur == DeviceType.ODF and cur in odf_with_olt:
                anchored_ok = True
                break
            for nb in adj.get(cur, set()):
                if nb not in visited:
                    visited.add(nb)
                    queue.append(nb)

    if not anchored_ok:
        raise_error(
            ErrorCode.LINK_INVALID_UPSTREAM,
            detail_suffix=(
                "ONT may connect to passive NVT/SPLITTER/HOP only within an ODF-"
                "headed path that already anchors to an OLT (not SPLITTER directly)"
            ),
        )

    # Splitter V1 constraints
    if other.type == DeviceType.SPLITTER:
        # Determine which OUT port reaches the ONT-side interface being linked
        ont_if_id = a_interface_id if a_dev.type in ONT_CLASS else b_interface_id
        out_if = find_out_interface_reaching(s, other, ont_if_id)
        if out_if is None:
            # Fall back: detect OUT iface from payload endpoints if present
            a_if_obj = s.get(Interface, a_interface_id)
            b_if_obj = s.get(Interface, b_interface_id)
            for cand in (a_if_obj, b_if_obj):
                if (
                    cand is not None
                    and cand.device_id == other.id
                    and str(getattr(cand, "name", "")).lower().startswith("out")
                ):
                    out_if = cand
                    break
        if out_if is not None:
            if out_interface_has_ont(s, out_if.id):
                raise_error(
                    ErrorCode.LINK_INVALID_UPSTREAM,
                    detail_suffix=(
                        f"Splitter OUT '{out_if.name}' already serves an ONT; over-subscription is not allowed"
                    ),
                )
        ports_total, _used, downstream_onts = compute_splitter_usage(s, other)
        if ports_total > 0 and downstream_onts >= ports_total:
            raise_error(
                ErrorCode.LINK_INVALID_UPSTREAM,
                detail_suffix=(
                    f"Splitter capacity exhausted: {downstream_onts}/{ports_total} ONTs already connected"
                ),
            )


def enforce_pon_role_if_declared(
    s, a_dev: Device, b_dev: Device, a_if: Interface, b_if: Interface
) -> None:
    """If the link is on the access segment involving an OLT and the OLT declares
    any PON ports, require that the OLT-facing interface is a PON port."""
    is_olt_access_segment = (
        a_dev.type == DeviceType.OLT
        and (
            b_dev.type in ONT_CLASS or b_dev.type in PASSIVE_INLINE or b_dev.type == DeviceType.ODF
        )
    ) or (
        b_dev.type == DeviceType.OLT
        and (
            a_dev.type in ONT_CLASS or a_dev.type in PASSIVE_INLINE or a_dev.type == DeviceType.ODF
        )
    )
    if not is_olt_access_segment:
        return

    olt_iface = a_if if a_dev.type == DeviceType.OLT else b_if
    olt_dev = a_dev if a_dev.type == DeviceType.OLT else b_dev
    olt_ifaces = s.exec(select(Interface).where(Interface.device_id == olt_dev.id)).all()
    olt_has_any_pon = any(getattr(i, "port_role", None) == PortRole.PON for i in olt_ifaces)
    if olt_has_any_pon and getattr(olt_iface, "port_role", None) != PortRole.PON:
        raise_error(ErrorCode.INVALID_LINK_TYPE, detail_suffix="PON_PORT_REQUIRED")


def enforce_single_upstream_rules(s, a_dev: Device, b_dev: Device) -> None:
    """Enforce single-upstream semantics: ODF may have only one upstream OLT link;
    ONT may have only one upstream link to ODF."""

    def _count_upstream_links(dev: Device) -> int:
        links = s.exec(select(Link)).all()
        cnt = 0
        for ln in links:
            ia = s.get(Interface, ln.a_interface_id)
            ib = s.get(Interface, ln.b_interface_id)
            if not ia or not ib:
                continue
            participates = ia.device_id == dev.id or ib.device_id == dev.id
            if not participates:
                continue
            other_id = ib.device_id if ia.device_id == dev.id else ia.device_id
            other_dev = s.get(Device, other_id)
            if not other_dev:
                continue
            if dev.type == DeviceType.ODF and other_dev.type == DeviceType.OLT:
                cnt += 1
            elif dev.type in ONT_CLASS and other_dev.type in PASSIVE_INLINE:
                cnt += 1
        return cnt

    # ODF<->OLT case
    if (a_dev.type == DeviceType.ODF and b_dev.type == DeviceType.OLT) or (
        b_dev.type == DeviceType.ODF and a_dev.type == DeviceType.OLT
    ):
        odf = a_dev if a_dev.type == DeviceType.ODF else b_dev
        if _count_upstream_links(odf) >= 1:
            raise_error(
                ErrorCode.LINK_MULTIPLE_UPSTREAMS,
                detail_suffix=f"{odf.id} already has an upstream link. Only one upstream is allowed.",
            )

    # ONT<->ODF case
    if (a_dev.type in ONT_CLASS and b_dev.type == DeviceType.ODF) or (
        b_dev.type in ONT_CLASS and a_dev.type == DeviceType.ODF
    ):
        ont = a_dev if a_dev.type in ONT_CLASS else b_dev
        if _count_upstream_links(ont) >= 1:
            raise_error(
                ErrorCode.LINK_MULTIPLE_UPSTREAMS,
                detail_suffix=f"{ont.id} already has an upstream link. Only one upstream is allowed.",
            )
