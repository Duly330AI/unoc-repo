"""Profile status recompute to find CPU hotspots.

Usage:
    python tools/profile_status_recompute.py --devices 100 --output profile.stats

Outputs:
    - profile.stats: cProfile binary output
    - profile.txt: Human-readable sorted by cumulative time
    - profile_calls.txt: Sorted by number of calls
"""

import argparse
import cProfile
import pstats
import sys
from io import StringIO

sys.path.insert(0, ".")

from backend.db import get_session, init_db
from backend.models import Device
from backend.services.status_service import recompute_dirty


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--devices", type=int, default=100, help="Number of devices to recompute")
    parser.add_argument("--output", default="profile.stats", help="Output file for profile stats")
    args = parser.parse_args()

    init_db()

    with get_session() as s:
        devices = s.query(Device).limit(args.devices).all()
        device_ids = [d.id for d in devices]

    print(f"Profiling status recompute for {len(device_ids)} devices...")

    profiler = cProfile.Profile()
    profiler.enable()

    # Profile the actual recompute
    with get_session() as s:
        dirty = type("DirtySet", (), {"devices": device_ids, "links": []})()
        recompute_dirty(s, dirty)

    profiler.disable()

    # Save binary stats
    profiler.dump_stats(args.output)
    print(f"✅ Binary stats saved to: {args.output}")

    # Generate human-readable report sorted by cumulative time
    s = StringIO()
    ps = pstats.Stats(profiler, stream=s)
    ps.strip_dirs()
    ps.sort_stats("cumulative")
    ps.print_stats(50)  # Top 50 functions

    txt_output = args.output.replace(".stats", ".txt")
    with open(txt_output, "w") as f:
        f.write(s.getvalue())
    print(f"✅ Cumulative time report saved to: {txt_output}")

    # Generate report sorted by call count
    s2 = StringIO()
    ps2 = pstats.Stats(profiler, stream=s2)
    ps2.strip_dirs()
    ps2.sort_stats("calls")
    ps2.print_stats(50)

    calls_output = args.output.replace(".stats", "_calls.txt")
    with open(calls_output, "w") as f:
        f.write(s2.getvalue())
    print(f"✅ Call count report saved to: {calls_output}")

    # Print summary to console
    print("\n" + "=" * 80)
    print("TOP 10 FUNCTIONS BY CUMULATIVE TIME:")
    print("=" * 80)
    ps3 = pstats.Stats(profiler)
    ps3.strip_dirs()
    ps3.sort_stats("cumulative")
    ps3.print_stats(10)


if __name__ == "__main__":
    main()
