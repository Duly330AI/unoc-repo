"""Query-focused implementations for links endpoints.

Extracted from `links_helpers.py` to keep modules under the 400-line budget.
Imported and re-exported by `links_helpers.py` to preserve public API.
"""

from __future__ import annotations

import hashlib
import json
from threading import Lock

from fastapi import HTTPException
from sqlmodel import select

from backend.api.schemas import LinkResolvedOut
from backend.db import get_session, init_db
from backend.models import Interface, Link
from backend.services.pathfinding import PATHFINDING_STORE
from backend.services.status_service import evaluate_link_status

from .links_helpers_common import normalize_status_str

__all__ = ["list_links_impl", "get_link_impl"]


# Topology-versioned in-process cache for list_links_impl results
_LINKS_CACHE: dict[int, list[LinkResolvedOut]] = {}
_LINKS_CACHE_LOCK = Lock()
_LINKS_JSON_CACHE: dict[int, tuple[bytes, str]] = {}


def list_links_impl() -> list[LinkResolvedOut]:
    init_db()
    with get_session() as s:
        tv = PATHFINDING_STORE.version()
        cached = _LINKS_CACHE.get(tv)
        if cached is not None:
            return cached

        links = s.exec(select(Link)).all()
        iface_ids = {ln.a_interface_id for ln in links} | {ln.b_interface_id for ln in links}
        if not iface_ids:
            return []
        iface_map: dict[str, str] = {}
        for iid in iface_ids:
            iface = s.get(Interface, iid)
            if iface:
                iface_map[iid] = iface.device_id
        out: list[LinkResolvedOut] = []
        for link in links:
            eff = evaluate_link_status(link)
            eff_str = normalize_status_str(eff)
            out.append(
                LinkResolvedOut(
                    id=link.id,
                    a_interface_id=link.a_interface_id,
                    b_interface_id=link.b_interface_id,
                    a_device_id=iface_map.get(link.a_interface_id, ""),
                    b_device_id=iface_map.get(link.b_interface_id, ""),
                    status=link.status,
                    effective_status=eff_str,
                    kind=link.kind,
                    admin_override_status=link.admin_override_status,
                    length_km=link.length_km,
                    physical_medium_id=link.physical_medium_id,
                    rule_id=None,
                )
            )
        for i in range(len(out)):
            try:
                es = getattr(out[i], "effective_status", None)
                if isinstance(es, str) and "." in es:
                    object.__setattr__(out[i], "effective_status", es.split(".")[-1])
            except Exception:
                pass
        # Populate cache under lock (double-check)
        with _LINKS_CACHE_LOCK:
            if tv not in _LINKS_CACHE:
                _LINKS_CACHE[tv] = out
                # Cleanup older versions
                old_keys = [k for k in _LINKS_CACHE.keys() if k != tv]
                for k in old_keys:
                    _LINKS_CACHE.pop(k, None)
        return _LINKS_CACHE.get(tv, out)


def _serialize_links_to_json(links: list[LinkResolvedOut]) -> bytes:
    arr = [ln.model_dump(exclude_none=True) for ln in links]
    return json.dumps(arr, separators=(",", ":"), sort_keys=False).encode("utf-8")


def _compute_etag(tv: int, payload: bytes) -> str:
    h = hashlib.sha256()
    h.update(b"tv=")
    h.update(str(tv).encode())
    h.update(b";payload=")
    h.update(payload)
    return 'W/"tv:%d-%s"' % (tv, h.hexdigest()[:16])


def get_links_json_cached() -> tuple[bytes, str]:
    """Return (json_bytes, etag) for links list, cached by topology version."""
    init_db()
    with get_session():
        tv = PATHFINDING_STORE.version()
        cached = _LINKS_JSON_CACHE.get(tv)
        if cached is not None:
            return cached

        objs = list_links_impl()
        payload = _serialize_links_to_json(objs)
        etag = _compute_etag(tv, payload)
        with _LINKS_CACHE_LOCK:
            if tv not in _LINKS_JSON_CACHE:
                _LINKS_JSON_CACHE[tv] = (payload, etag)
                # Cleanup older versions
                old_keys = [k for k in _LINKS_JSON_CACHE.keys() if k != tv]
                for k in old_keys:
                    _LINKS_JSON_CACHE.pop(k, None)
        return _LINKS_JSON_CACHE.get(tv, (payload, etag))


def get_link_impl(link_id: str) -> LinkResolvedOut:
    init_db()
    with get_session() as s:
        link = s.get(Link, link_id)
        if not link:
            raise HTTPException(status_code=404, detail="Not found")
        a_iface = s.get(Interface, link.a_interface_id)
        b_iface = s.get(Interface, link.b_interface_id)
        eff = evaluate_link_status(link)
        eff_str = normalize_status_str(eff)
        return LinkResolvedOut(
            id=link.id,
            a_interface_id=link.a_interface_id,
            b_interface_id=link.b_interface_id,
            a_device_id=a_iface.device_id if a_iface else "",
            b_device_id=b_iface.device_id if b_iface else "",
            status=link.status,
            effective_status=eff_str,
            kind=link.kind,
            admin_override_status=link.admin_override_status,
            length_km=link.length_km,
            physical_medium_id=link.physical_medium_id,
            rule_id=None,
        )
