from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from backend.db import get_session
from backend.models import Device
from backend.services import status_diagnostics
from backend.services.debug_snapshot import gather_full_snapshot
from backend.services.dependency_resolver import trace_l3_path_to_anchor
from backend.services.subscriber_model import resolve_subscriber_model

router = APIRouter(tags=["debug"], prefix="/debug")


def _dev_enabled() -> bool:
    return os.getenv("UNOC_DEV_FEATURES", "0").strip() not in {"", "0", "false", "False"}


@router.get("/full-snapshot")
def get_full_snapshot(
    sections: str | None = Query(default=None, description="CSV list of sections to include"),
    pretty: bool = Query(default=False),
    maxItems: int | None = Query(default=None, ge=1),
    includeDeltas: bool = Query(default=True),
) -> Any:  # raw JSON dump by design
    if not _dev_enabled():
        raise HTTPException(status_code=404, detail="Not Found")

    selected = None
    if sections:
        selected = [s.strip() for s in sections.split(",") if s.strip()]
    doc = gather_full_snapshot(
        selected_sections=selected, max_items=maxItems, include_deltas=includeDeltas
    )
    if pretty:
        # Let FastAPI handle JSON serialization; returning dict is fine. Pretty flag retained for future.
        return doc
    return doc


@router.get("/l3-path/{device_id}")
def get_l3_path(device_id: str):  # type: ignore[override]
    """Return a traced L3 path to a backbone anchor for the given device.

    Dev-only endpoint gated by UNOC_DEV_FEATURES, intended for diagnostics.
    Response: { ok: bool, reason: str|null, chain: string[] }
    """
    if not _dev_enabled():
        raise HTTPException(status_code=404, detail="Not Found")
    with get_session() as s:
        d = s.get(Device, device_id)
        if not d:
            raise HTTPException(status_code=404, detail="device not found")
        res = trace_l3_path_to_anchor(s, d)
        return {
            "ok": bool(res.ok),
            "reason": res.reason,
            "chain": res.chain or [],
        }


@router.get("/status-diagnostics")
def get_status_diagnostics():  # type: ignore[override]
    """Return current in-memory status diagnostics snapshot.

    Dev-only endpoint; exposes per-device upstream_l3_ok, anchor, reason_codes,
    legacy BFS reachability flag and the evaluation timestamp. Purely
    observational in Phase 1.
    """
    if not _dev_enabled():
        raise HTTPException(status_code=404, detail="Not Found")
    return {"devices": status_diagnostics.snapshot()}


@router.get("/subscriber-model")
def get_subscriber_model():  # type: ignore[override]
    if not _dev_enabled():
        raise HTTPException(status_code=404, detail="Not Found")
    with get_session() as s:
        return resolve_subscriber_model(s)
