# isort: skip_file
import os

from sqlmodel import Session, select

from backend.db import engine, init_db, reset_db
from backend.models import Device
from backend.services.seed_service import ensure_backbone_gateway


os.environ["ENSURE_SINGLE_BACKBONE_GATEWAY"] = "true"
reset_db()
init_db()
with Session(engine) as s:
    devices = s.exec(select(Device)).all()
    print("Initial devices:", [d.id for d in devices])
    created = ensure_backbone_gateway(s)
    print("Created returned:", created is not None)
    print("Post devices:", [d.id for d in s.exec(select(Device)).all()])
