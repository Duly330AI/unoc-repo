"""Dirty-set preparation and aggregation helpers for Traffic V2.

Contract (minimal, deterministic, side-effect free):
- prepare_dirty(dirty):
    Input 'dirty' is a mapping or object with attributes:
      - devices: Iterable[str]
      - links: Iterable[str]
      - region_id: Optional[str]
    Returns PreparedDirty with:
      - region_id
      - device_ids: sorted unique list of affected device ids
      - link_ids: sorted unique list of affected link ids (from input)
      - flags: {'tariffs_changed': bool, 'capacities_changed': bool}

- aggregate_dirty(prepared, incremental=True):
    If incremental is True: returns AggregationDelta containing only the
    passed device_ids and link_ids (sorted, unique) — a minimal delta envelope.
    If incremental is False: returns all device and link ids from the DB
    (global full set, stable sorted) to approximate full compute parity.

Note:
- We purposefully do not compute metrics here. This module focuses on
  identifying the minimal affected set for aggregation. Wiring metrics can be
  added later without changing the public contract of id lists.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from sqlmodel import select

from backend.db import get_session
from backend.models import Device, Interface, Link


@dataclass(frozen=True)
class PreparedDirty:
    region_id: str | None
    device_ids: list[str]
    link_ids: list[str]
    flags: dict[str, bool]


@dataclass(frozen=True)
class AggregationDelta:
    device_ids: list[str]
    link_ids: list[str]
    events: list[dict]


def _as_iter(obj) -> Iterable[str]:
    if obj is None:
        return []
    if isinstance(obj, list | tuple | set):
        return obj
    # Support pydantic/attr objects with .__iter__ if needed
    try:
        return list(obj)
    except Exception:
        return []


def _sorted_unique(ids: Iterable[str]) -> list[str]:
    # Stable determinism: lexicographic sort on strings
    return sorted(set(i for i in ids if i))


def _coerce_dirty(dirty) -> tuple[list[str], list[str], str | None]:
    # Supports dicts and objects with attributes
    if isinstance(dirty, dict):
        devs = dirty.get("devices", [])
        links = dirty.get("links", [])
        region = dirty.get("region_id")
    else:
        devs = getattr(dirty, "devices", [])
        links = getattr(dirty, "links", [])
        region = getattr(dirty, "region_id", None)
    return list(_as_iter(devs)), list(_as_iter(links)), region  # type: ignore[return-value]


def prepare_dirty(dirty) -> PreparedDirty:
    dev_ids, link_ids, region_id = _coerce_dirty(dirty)

    # Start with explicitly dirty devices
    device_set: set[str] = set(d for d in dev_ids if d)
    link_set: set[str] = set(link for link in link_ids if link)

    if link_set:
        with get_session() as s:
            # Load all dirty links and collect their interface endpoints
            links = s.exec(select(Link).where(Link.id.in_(list(link_set)))).all()  # type: ignore[attr-defined]
            iface_ids: set[str] = set()
            for ln in links:
                # Support both historical and current field names
                a_id = (
                    getattr(ln, "a_interface_id", None)
                    or getattr(ln, "iface_a_id", None)
                    or getattr(ln, "a_if_id", None)
                )
                b_id = (
                    getattr(ln, "b_interface_id", None)
                    or getattr(ln, "iface_b_id", None)
                    or getattr(ln, "b_if_id", None)
                )
                if a_id:
                    iface_ids.add(a_id)
                if b_id:
                    iface_ids.add(b_id)
            if iface_ids:
                ifaces = s.exec(select(Interface).where(Interface.id.in_(list(iface_ids)))).all()  # type: ignore[attr-defined]
                for iface in ifaces:
                    if getattr(iface, "device_id", None):
                        device_set.add(iface.device_id)

    # Flags: keep simple for now; elevated when change-kinds are available
    flags = {
        "tariffs_changed": False,
        "capacities_changed": False,
    }

    return PreparedDirty(
        region_id=region_id,
        device_ids=_sorted_unique(device_set),
        link_ids=_sorted_unique(link_set),
        flags=flags,
    )


def aggregate_dirty(prepared: PreparedDirty, *, incremental: bool = True) -> AggregationDelta:
    if not incremental:
        # Return full device/link id space (deterministically sorted)
        with get_session() as s:
            all_dev_rows = s.exec(select(Device)).all()
            all_link_rows = s.exec(select(Link)).all()
            all_devs = [d.id for d in all_dev_rows]
            all_links = [link.id for link in all_link_rows]
        return AggregationDelta(
            device_ids=_sorted_unique(all_devs),
            link_ids=_sorted_unique(all_links),
            events=[],
        )

    # Incremental: pass-through the minimal affected set (already sorted)
    return AggregationDelta(
        device_ids=list(prepared.device_ids),
        link_ids=list(prepared.link_ids),
        events=[],
    )
