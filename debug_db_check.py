"""Quick script to check which DB is being used and what's in it."""

import os

# Set DATABASE_URL like the test does
os.environ["DATABASE_URL"] = "postgresql://unoc:unocpw@localhost:5432/unocdb"
os.environ["UNOC_PERSISTENCE"] = ""  # Not inmemory

# Import backend.db AFTER setting env
from sqlmodel import Session, select

from backend.db import SQLALCHEMY_DATABASE_URL, engine
from backend.models import Device, Link

print(f"Database URL: {SQLALCHEMY_DATABASE_URL}")
print(f"Engine: {engine}")

with Session(engine) as session:
    devices = session.exec(select(Device)).all()
    links = session.exec(select(Link)).all()

    print(f"\nDevices in DB: {len(devices)}")
    for d in devices[:5]:
        print(f"  - {d.id}: {d.type}, provisioned={d.provisioned}")

    print(f"\nLinks in DB: {len(links)}")
    for l in links[:5]:
        print(f"  - {l.id}: {l.src_device_id} → {l.dst_device_id}, status={l.status}")
