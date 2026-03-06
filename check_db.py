"""Quick script to check database content."""

from backend.db import get_session
from backend.models import Device

with get_session() as session:
    total = session.query(Device).count()
    olts = session.query(Device).filter(Device.type == "OLT").count()
    onts = session.query(Device).filter(Device.type == "ONT").count()
    splitters = session.query(Device).filter(Device.type == "SPLITTER").count()

    print(f"Total devices: {total}")
    print(f"OLTs: {olts}")
    print(f"ONTs: {onts}")
    print(f"SPLITTERs: {splitters}")

    if onts > 0:
        ont = session.query(Device).filter(Device.type == "ONT").first()
        print(f"\nSample ONT: {ont.id} ({ont.name})")
