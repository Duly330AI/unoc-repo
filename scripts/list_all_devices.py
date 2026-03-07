#!/usr/bin/env python3
"""List all devices in database."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlmodel import select

from backend.db import get_session
from backend.models import Device


def main():
    with get_session() as s:
        devices = s.exec(select(Device)).all()
        print(f"Found {len(devices)} devices:")
        for dev in devices:
            print(
                f"  {dev.id:<20} {dev.type.value:<20} {dev.status.value:<10} Provisioned: {dev.provisioned}"
            )


if __name__ == "__main__":
    main()
