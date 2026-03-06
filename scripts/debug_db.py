"""
Debug: Check what the Go server sees in the database.
"""

from backend.db import get_session
from backend.models import Device, DeviceType, Tariff


def debug_db():
    with get_session() as s:
        # Count all devices
        total_devices = s.query(Device).count()  # type: ignore
        print(f"Total devices in DB: {total_devices}")

        # Count ONTs
        onts = s.query(Device).filter(Device.type.in_([DeviceType.ONT, DeviceType.BUSINESS_ONT, DeviceType.AON_CPE])).all()  # type: ignore
        print(f"\nONT devices: {len(onts)}")
        for ont in onts[:10]:  # Show first 10
            print(
                f"  {ont.id}: status={ont.status}, provisioned={ont.provisioned}, tariff_id={ont.tariff_id}"
            )

        # Count tariffs
        tariffs = s.query(Tariff).all()  # type: ignore
        print(f"\nTariffs: {len(tariffs)}")
        for t in tariffs:
            print(f"  Tariff {t.id}: {t.name} (up={t.max_up_mbps}, down={t.max_down_mbps})")

        # Check test ONTs specifically
        test_onts = s.query(Device).filter(Device.id.like("ont_test%")).all()  # type: ignore
        print(f"\nTest ONTs (ont_test*): {len(test_onts)}")
        for ont in test_onts:
            print(f"  {ont.id}:")
            print(f"    type={ont.type}")
            print(f"    status={ont.status}")
            print(f"    provisioned={ont.provisioned}")
            print(f"    tariff_id={ont.tariff_id}")
            # Check if tariff exists
            if ont.tariff_id:
                tariff = s.query(Tariff).filter(Tariff.id == ont.tariff_id).first()  # type: ignore
                if tariff:
                    print(f"    ✅ Tariff found: {tariff.name}")
                else:
                    print(f"    ❌ Tariff {ont.tariff_id} NOT FOUND")


if __name__ == "__main__":
    debug_db()
