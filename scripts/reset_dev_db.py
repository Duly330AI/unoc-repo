"""Development DB reset utility.

Usage (PowerShell):
  python scripts/reset_dev_db.py              # drop & recreate file DB
  python scripts/reset_dev_db.py --seed       # with minimal seed devices
  UNOC_PERSISTENCE=inmemory python scripts/reset_dev_db.py  # just resets in-memory (no file)

Options:
        --seed            Insert a few sample devices (POP, CORE_ROUTER, OLT), unprovisioned and IP-free
        --demo-topology   With --seed, also create interfaces and example links (still unprovisioned)
    --catalog-only    Seed only catalog defaults (no devices), then exit
    --force           Do not prompt when removing existing file

The script respects UNOC_DB_URL or UNOC_PERSISTENCE env vars just like backend.db.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Ensure project root (one directory up) is on sys.path when script executed directly
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.db import (  # type: ignore  # noqa: E402
    SQLALCHEMY_DATABASE_URL,
    get_session,
    init_db,
    reset_db,
)
from backend.models import Device, DeviceType  # type: ignore  # noqa: E402
from backend.services.seed_service import (  # type: ignore  # noqa: E402
    ensure_default_hardware_models,
)

FILE_DB_NAME = "unoc_dev.db"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--seed", action="store_true", help="Insert minimal seed data")
    p.add_argument(
        "--demo-topology",
        action="store_true",
        help="With --seed, also create interfaces and example links (no provisioning)",
    )
    p.add_argument(
        "--catalog-only",
        action="store_true",
        help="Seed only catalog defaults (no devices)",
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompt when deleting file DB",
    )
    return p.parse_args()


def maybe_remove_file_db(force: bool) -> None:
    if SQLALCHEMY_DATABASE_URL.startswith("sqlite:///") and not SQLALCHEMY_DATABASE_URL.endswith(
        "://"
    ):
        path = SQLALCHEMY_DATABASE_URL.replace("sqlite:///", "")
        db_path = Path(path)
        if db_path.exists():
            if not force:
                resp = input(f"Delete existing DB file '{db_path}'? [y/N]: ").strip().lower()
                if resp != "y":
                    print("Aborted.")
                    sys.exit(0)
            try:
                db_path.unlink()
                print(f"Deleted {db_path}")
            except PermissionError:
                # Likely still in use by a running dev server; skip hard failure to avoid partial startup crashes.
                print(
                    f"Warning: could not delete {db_path} (in use). Continuing with existing file."
                )


def seed_minimal(demo_topology: bool = False) -> None:
    with get_session() as s:
        # Seed default hardware catalog first (idempotent)
        try:
            ensure_default_hardware_models(s)
        except Exception:
            # Non-fatal for minimal seed
            pass
        if s.get(Device, "pop1"):
            print("Seed appears already applied; skipping.")
            return
        devices = [
            Device(id="pop1", name="POP-1", type=DeviceType.POP),
            Device(id="core1", name="Core-1", type=DeviceType.CORE_ROUTER),
            Device(id="olt1", name="OLT-1", type=DeviceType.OLT, parent_container_id="pop1"),
        ]
        for d in devices:
            s.add(d)
        s.commit()
        print("Seeded devices:", ", ".join(d.id for d in devices))
        if demo_topology:
            # Create default interfaces and a logical adjacency core1<->olt1
            from backend.models import Interface, Link, LinkType  # lazy import

            s.add(Interface(id="core1-if0", device_id="core1", name="if0"))
            s.add(Interface(id="olt1-if0", device_id="olt1", name="if0"))
            s.flush()
            s.add(
                Link(
                    id="core1-olt1",
                    a_interface_id="core1-if0",
                    b_interface_id="olt1-if0",
                    kind=LinkType.FIBER,
                )
            )
            s.commit()


def main() -> int:
    args = parse_args()
    # If persistence is file, remove file first for a true reset
    persistence = os.getenv("UNOC_PERSISTENCE", "file").lower()
    if persistence == "file" and not os.getenv("UNOC_DB_URL"):
        maybe_remove_file_db(force=args.force)
    # Recreate schema
    reset_db()
    init_db()
    print("Database schema recreated (mode:", persistence, ")", sep="")
    # Catalog-only seed path
    if args.catalog_only:
        try:
            with get_session() as s:
                ensure_default_hardware_models(s)
                # Persist catalog rows; 'flush' inside seeding isn't enough when session closes
                s.commit()
            print("Catalog defaults seeded (no devices)")
        except Exception:
            print("Warning: catalog seeding failed; continuing with empty catalog")
        return 0
    if args.seed:
        seed_minimal(args.demo_topology)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
