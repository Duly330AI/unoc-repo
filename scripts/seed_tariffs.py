"""
Seed minimal tariffs and assign to provisioned ONTs.
"""

from backend.db import get_session
from backend.models import Device, Tariff


def seed_tariffs_and_assign():
    with get_session() as session:
        # Create 3 basic tariffs
        tariffs = [
            Tariff(id=1, name="Residential 100/20", max_up_mbps=20, max_down_mbps=100),
            Tariff(id=2, name="Residential 500/100", max_up_mbps=100, max_down_mbps=500),
            Tariff(id=3, name="Business 1000/1000", max_up_mbps=1000, max_down_mbps=1000),
        ]

        for t in tariffs:
            session.merge(t)

        session.commit()
        print(f"✅ Created {len(tariffs)} tariffs")

        # Assign tariffs to provisioned leaf devices (round-robin)
        leaves = (
            session.query(Device)
            .filter(Device.type.in_(["ONT", "BUSINESS_ONT", "AON_CPE"]))  # type: ignore
            .filter(Device.provisioned)  # type: ignore
            .all()
        )

        if not leaves:
            print("⚠️  No provisioned leaves to assign tariffs")
            return

        assigned = 0
        for i, device in enumerate(leaves):
            tariff_id = (i % len(tariffs)) + 1  # Round-robin 1,2,3,1,2,3,...
            device.tariff_id = tariff_id
            assigned += 1

        session.commit()
        print(f"✅ Assigned tariffs to {assigned} provisioned leaves")
        print(f"   Distribution: ~{assigned // len(tariffs)} devices per tariff")


if __name__ == "__main__":
    seed_tariffs_and_assign()
