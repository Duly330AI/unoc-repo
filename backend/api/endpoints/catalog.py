from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlmodel import select

from backend.db import get_session, init_db
from backend.models import HardwareModel
from backend.services.catalog_service import list_hardware
from backend.services.seed_service import ensure_default_hardware_models

router = APIRouter(tags=["catalog"], prefix="/catalog")


@router.get("/hardware", response_model=list[dict])
def list_models(type: str | None = None):  # filter by device_type optional
    """List hardware catalog models, auto-seeding defaults if empty.

    This makes the endpoint self-healing for in-memory runs or freshly reset
    databases where the catalog wasn't pre-seeded by scripts.
    """
    init_db()
    with get_session() as s:
        rows = list_hardware(s, type)
        if not rows:
            # Seed defaults (idempotent) and retry once
            try:
                ensure_default_hardware_models(s)
                s.commit()
                rows = list_hardware(s, type)
            except Exception:
                # If seeding fails, return the original (empty) result
                pass
        return [
            {
                "id": r.id,
                "catalog_id": r.catalog_id,
                "device_type": r.device_type.value,
                "vendor": r.vendor,
                "model": r.model,
                "version": r.version,
                "capacity_gbps": r.capacity_gbps,
                "ports_total": r.ports_total,
            }
            for r in rows
        ]


@router.get("/hardware/{catalog_id}", response_model=dict)
def get_model(catalog_id: str):
    init_db()
    with get_session() as s:
        r = s.exec(select(HardwareModel).where(HardwareModel.catalog_id == catalog_id)).first()
        if not r:
            raise HTTPException(status_code=404, detail="Not found")
        return {
            "id": r.id,
            "catalog_id": r.catalog_id,
            "device_type": r.device_type.value,
            "vendor": r.vendor,
            "model": r.model,
            "version": r.version,
            "capacity_gbps": r.capacity_gbps,
            "ports_total": r.ports_total,
            "tx_power_dbm": r.tx_power_dbm,
            "sensitivity_min_dbm": r.sensitivity_min_dbm,
            "insertion_loss_db": r.insertion_loss_db,
            "meta": {"source": r.meta_source, "notes": r.meta_notes},
        }


__all__ = ["router"]
