"""Hardware Catalog Loader & Accessors (TASK-521).

Loads hardware definitions from JSON files (ARCHITECTURE §14) into SQLModel tables.
Design:
- Idempotent upsert by catalog_id.
- Minimal schema: HardwareModel + PortProfile.

JSON structure (per file):
{
  "catalog_id": "OLT_HUAWEI_MA5800_X2_V1",
  "device_type": "OLT",
  "vendor": "Huawei",
  "model": "MA5800-X2",
  "version": "1.0",
  "attributes": {"tx_power_dbm": 5.0, "sensitivity_min_dbm": -30.0, "insertion_loss_db": 3.5, "capacity_gbps": 40},
  "ports": [
    {"name": "uplink", "count": 2, "speed_gbps": 10, "role": "uplink", "media": "sfp+"},
    {"name": "pon", "count": 16, "speed_gbps": 2.5, "role": "access", "media": "gpon"}
  ],
  "meta": {"source": "datasheet", "notes": "baseline"}
}
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import cast

from sqlmodel import Session, select

from backend.models import DeviceType, HardwareModel, PortProfile


def _coerce_devtype(s: str) -> DeviceType:
    try:
        return DeviceType(s)
    except Exception as exc:
        raise ValueError(f"unknown device_type: {s}") from exc


def load_catalog_dir(session: Session, catalog_dir: str | Path) -> int:
    """Load all JSON files under a directory into DB (idempotent).

    Returns number of models upserted.
    """
    base = Path(catalog_dir)
    if not base.exists() or not base.is_dir():
        return 0
    files: Iterable[Path] = base.rglob("*.json")
    count = 0
    for fp in files:
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            continue
        catalog_id = (data.get("catalog_id") or "").strip()
        if not catalog_id:
            continue
        device_type = _coerce_devtype(str(data.get("device_type") or "").strip())
        vendor = (data.get("vendor") or "").strip()
        model = (data.get("model") or "").strip()
        version = (data.get("version") or "").strip()
        attrs = data.get("attributes") or {}
        ports = data.get("ports") or []
        meta = data.get("meta") or {}

        existing = session.exec(
            select(HardwareModel).where(HardwareModel.catalog_id == catalog_id)
        ).first()
        if not existing:
            existing = HardwareModel(
                catalog_id=catalog_id,
                device_type=device_type,
                vendor=vendor,
                model=model,
                version=version,
            )
            session.add(existing)
            session.flush()
        # Update mutable fields
        existing.capacity_gbps = attrs.get("capacity_gbps")
        existing.ports_total = attrs.get("ports_total") or existing.ports_total
        existing.tx_power_dbm = attrs.get("tx_power_dbm")
        existing.sensitivity_min_dbm = attrs.get("sensitivity_min_dbm")
        existing.insertion_loss_db = attrs.get("insertion_loss_db")
        existing.meta_source = meta.get("source")
        existing.meta_notes = meta.get("notes")
        session.add(existing)
        session.flush()

        # Upsert PortProfiles by (hardware_model_id, name)
        # Ensure primary key is present for type checkers
        assert existing.id is not None
        for p in ports:
            name = (p.get("name") or "").strip()
            if not name:
                continue
            row = session.exec(
                select(PortProfile).where(
                    (PortProfile.hardware_model_id == existing.id) & (PortProfile.name == name)
                )
            ).first()
            if not row:
                row = PortProfile(hardware_model_id=cast(int, existing.id), name=name)
            row.count = int(p.get("count") or 0)
            row.speed_gbps = float(p.get("speed_gbps")) if p.get("speed_gbps") is not None else None
            row.role = p.get("role") or None
            row.media = p.get("media") or None
            session.add(row)
        count += 1
    session.commit()
    return count


def list_hardware(session: Session, type_filter: str | None = None) -> list[HardwareModel]:
    q = select(HardwareModel)
    if type_filter:
        q = q.where(HardwareModel.device_type == _coerce_devtype(type_filter))
    # Explicit list() to satisfy type checkers that may treat .all() as Sequence
    return list(session.exec(q).all())


def get_hardware(session: Session, catalog_id: str) -> HardwareModel | None:
    return session.exec(select(HardwareModel).where(HardwareModel.catalog_id == catalog_id)).first()


__all__ = ["load_catalog_dir", "list_hardware", "get_hardware"]
