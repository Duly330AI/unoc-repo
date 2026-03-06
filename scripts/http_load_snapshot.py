"""Lightweight HTTP load generator for /api/metrics/snapshot.

Runs simple concurrent GET requests for a fixed duration to populate
Prometheus/Grafana dashboards during local perf triage.

Usage (from repo root):
  .venv/Scripts/python.exe scripts/http_load_snapshot.py --duration 60 --concurrency 8 --url http://localhost:5001/api/metrics/snapshot
"""

from __future__ import annotations

import argparse
import concurrent.futures
import time
import urllib.request


def fetch(url: str, timeout: float) -> None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as _:
            # Discard body
            _ = None
    except Exception:
        # Ignore errors during load generation
        pass


def worker(url: str, deadline: float, per_req_timeout: float) -> int:
    cnt = 0
    while time.time() < deadline:
        fetch(url, per_req_timeout)
        cnt += 1
    return cnt


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:5001/api/metrics/snapshot")
    ap.add_argument("--duration", type=int, default=60, help="duration in seconds")
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--timeout", type=float, default=5.0, help="per-request timeout in seconds")
    args = ap.parse_args()

    deadline = time.time() + max(1, int(args.duration))
    total = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, int(args.concurrency))) as ex:
        futs = [
            ex.submit(worker, args.url, deadline, float(args.timeout))
            for _ in range(max(1, int(args.concurrency)))
        ]
        for f in concurrent.futures.as_completed(futs):
            try:
                total += int(f.result())
            except Exception:
                pass
    print(
        f"done requests={total} concurrency={args.concurrency} duration={args.duration}s url={args.url}"
    )


if __name__ == "__main__":
    main()
