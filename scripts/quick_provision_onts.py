"""
Quick test: Provision 3 ONTs with tariffs via existing API.
"""

from backend.db import get_session
from backend.models import Device, DeviceType, Tariff


def quick_provision():
    with get_session() as s:
        # Tariffs should already exist (from seed_tariffs.py)
        tariff_count = s.query(Tariff).count()  # type: ignore
        print(f"✅ Found {tariff_count} existing tariffs")

        # Get OLT1 (should exist from seed)
        olt1 = s.query(Device).filter(Device.id == "olt1").first()  # type: ignore
        if not olt1:
            print("❌ OLT1 not found - run reset_dev_db.py --force --seed first")
            return

        # Create 3 ONTs connected to olt1
        onts = []
        for i in range(1, 4):
            ont_id = f"ont_test{i}"
            ont = Device(
                id=ont_id,
                name=f"Test ONT {i}",
                type=DeviceType.ONT,
                tariff_id=i,  # Assign tariff 1/2/3
                provisioned=True,
            )
            s.add(ont)
            onts.append(ont)

        s.commit()
        print(f"✅ Created {len(onts)} provisioned ONTs with tariffs")

        # Verify
        provisioned_count = (
            s.query(Device)
            .filter(
                Device.type == DeviceType.ONT,  # type: ignore
                Device.provisioned.is_(True),  # type: ignore
                Device.tariff_id.isnot(None),  # type: ignore
            )
            .count()
        )

        print(f"📊 Total provisioned ONTs with tariff: {provisioned_count}")


if __name__ == "__main__":
    quick_provision()
