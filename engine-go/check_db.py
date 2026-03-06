"""Quick database check for provisioned devices and tariffs."""

from sqlmodel import select

from backend.db import get_session, init_db
from backend.models import Device, Tariff

init_db()

with get_session() as session:
    # Count devices
    all_devices = list(session.exec(select(Device)).all())
    provisioned_devices = [d for d in all_devices if d.provisioned]
    leaf_devices = [d for d in all_devices if d.type in ["ONT", "BUSINESS_ONT", "AON_CPE"]]
    provisioned_leaves = [d for d in leaf_devices if d.provisioned]

    # Count tariffs
    all_tariffs = list(session.exec(select(Tariff)).all())

    # Devices with tariffs
    devices_with_tariff = [d for d in provisioned_leaves if d.tariff_id is not None]

    print("\n📊 Database Status:")
    print("─" * 50)
    print(f"Total devices:        {len(all_devices)}")
    print(f"Provisioned devices:  {len(provisioned_devices)}")
    print(f"Leaf devices (ONT/CPE): {len(leaf_devices)}")
    print(f"Provisioned leaves:   {len(provisioned_leaves)}")
    print(f"Leaves with tariff:   {len(devices_with_tariff)}")
    print(f"Total tariffs:        {len(all_tariffs)}")
    print("─" * 50)

    if len(devices_with_tariff) == 0:
        print("\n⚠️  NO ELIGIBLE LEAVES for traffic generation!")
        print("   Reason: No provisioned ONT/CPE with assigned tariff")
        print("\n💡 Solution:")
        print("   1. Run: python scripts/reset_dev_db.py --force --seed")
        print("   2. Or provision devices manually with tariffs")
    else:
        print(f"\n✅ {len(devices_with_tariff)} leaves ready for traffic generation")
