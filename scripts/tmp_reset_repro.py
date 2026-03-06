"""Ad-hoc debug script; keep imports in execution order."""

# isort: skip_file
import os
import sys

from sqlmodel import Session, select

sys.path.insert(0, "c:/noc_project/UNOC/unoc")
from backend.db import engine, init_db, reset_db
from backend.models import Device
from backend.services.seed_service import ensure_backbone_gateway

os.environ["ENSURE_SINGLE_BACKBONE_GATEWAY"] = "true"
reset_db()
init_db()
with Session(engine) as s:
    d = ensure_backbone_gateway(s)
    print("After creation count", len(s.exec(select(Device)).all()))

# Simulate next test
reset_db()
init_db()
with Session(engine) as s:
    devices = s.exec(select(Device)).all()
    print("After reset count", len(devices), devices)
