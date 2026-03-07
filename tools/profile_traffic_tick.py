"""Profile traffic engine tick to find CPU hotspots.

Usage:
    python tools/profile_traffic_tick.py --output traffic_profile.stats

Outputs:
    - traffic_profile.stats: cProfile binary output
    - traffic_profile.txt: Human-readable sorted by cumulative time
"""

import argparse
import cProfile
import pstats
import sys
from io import StringIO

sys.path.insert(0, ".")

from backend.db import init_db
from backend.services.traffic.v2_engine import TrafficEngine


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output", default="traffic_profile.stats", help="Output file for profile stats"
    )
    parser.add_argument("--ticks", type=int, default=10, help="Number of ticks to profile")
    args = parser.parse_args()

    init_db()

    print(f"Profiling {args.ticks} traffic ticks...")

    # Create engine instance
    engine = TrafficEngine()

    profiler = cProfile.Profile()
    profiler.enable()

    # Profile multiple ticks
    for _ in range(args.ticks):
        engine.run_tick()

    profiler.disable()

    # Save binary stats
    profiler.dump_stats(args.output)
    print(f"✅ Binary stats saved to: {args.output}")

    # Generate human-readable report
    s = StringIO()
    ps = pstats.Stats(profiler, stream=s)
    ps.strip_dirs()
    ps.sort_stats("cumulative")
    ps.print_stats(50)

    txt_output = args.output.replace(".stats", ".txt")
    with open(txt_output, "w") as f:
        f.write(s.getvalue())
    print(f"✅ Cumulative time report saved to: {txt_output}")

    # Print summary
    print("\n" + "=" * 80)
    print("TOP 10 FUNCTIONS BY CUMULATIVE TIME:")
    print("=" * 80)
    ps2 = pstats.Stats(profiler)
    ps2.strip_dirs()
    ps2.sort_stats("cumulative")
    ps2.print_stats(10)


if __name__ == "__main__":
    main()
