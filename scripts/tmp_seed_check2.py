import os
import sys

from sqlmodel import Session, select

sys.path.insert(0, "c:/noc_project/UNOC/unoc")
os.environ["ENSURE_SINGLE_BACKBONE_GATEWAY"] = "true"
from backend.db import engine, init_db, reset_db
from backend.models import Device
from backend.services.seed_service import ensure_backbone_gateway

reset_db()
init_db()
with Session(engine) as s:
    print("Initial devices", [d.id for d in s.exec(select(Device)).all()])
    created = ensure_backbone_gateway(s)
    print("Created returned?", created is not None)
    print("Devices after ensure", [d.id for d in s.exec(select(Device)).all()])
