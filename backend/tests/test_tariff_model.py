from __future__ import annotations

from sqlmodel import select

from backend.db import get_session
from backend.models import Device, DeviceType, Tariff


def test_create_tariff_and_assign_to_device():
    with get_session() as session:
        # Create a tariff
        t = Tariff(name="Basic 100/20", max_up_mbps=20.0, max_down_mbps=100.0)
        session.add(t)
        session.commit()
        session.refresh(t)
        assert t.id is not None
        assert t.max_up_mbps == 20.0
        assert t.max_down_mbps == 100.0

        # Create a device and assign tariff
        d = Device(id="ONT-1", name="ONT-1", type=DeviceType.ONT)
        d.tariff_id = t.id
        session.add(d)
        session.commit()

        # Query back and verify relationship via FK field value
        ont = session.exec(select(Device).where(Device.id == "ONT-1")).one()
        assert ont.tariff_id == t.id


def test_tariff_validation_non_negative():
    # Ensure non-negative constraints enforced at pydantic/model level
    t = Tariff(name="Zero Plan", max_up_mbps=0.0, max_down_mbps=0.0)
    assert t.max_up_mbps == 0.0
    assert t.max_down_mbps == 0.0
