import argparse
import glob
import os
import re


def percentile(sorted_vals, p):
    if not sorted_vals:
        return None
    k = int(round((p / 100.0) * len(sorted_vals) + 0.5)) - 1
    k = max(0, min(k, len(sorted_vals) - 1))
    return sorted_vals[k]


def main():
    parser = argparse.ArgumentParser(description="Compute p95 for ports summary from perf logs")
    parser.add_argument(
        "device_id", nargs="?", default="olt1", help="Device id for /api/ports/summary/{device_id}"
    )
    parser.add_argument("--logdir", default="logs", help="Directory containing perf.log files")
    args = parser.parse_args()

    files = glob.glob(os.path.join(args.logdir, "perf.log*"))
    if not files:
        print("no logs found")
        return 1

    latest = max(files, key=os.path.getmtime)
    target = f" path=/api/ports/summary/{args.device_id} "

    durs = []
    pattern = re.compile(r"dur_ms=([0-9]+(?:\.[0-9]+)?)")
    with open(latest, errors="ignore") as fh:
        for line in fh:
            if " method=GET " in line and target in line:
                m = pattern.search(line)
                if m:
                    try:
                        durs.append(float(m.group(1)))
                    except ValueError:
                        pass

    durs.sort()
    print(f"file={latest}")
    print(f"count={len(durs)}")
    if not durs:
        return 2

    p50 = percentile(durs, 50)
    p90 = percentile(durs, 90)
    p95 = percentile(durs, 95)
    p99 = percentile(durs, 99)

    print(f"p50_ms={p50}")
    print(f"p90_ms={p90}")
    print(f"p95_ms={p95}")
    print(f"p99_ms={p99}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
